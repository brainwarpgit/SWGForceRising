#!/usr/bin/env python3
"""Test actual structure storage arithmetic without building or running Core3.

The capacity method and insertion comparisons are extracted from production
source and compiled against small standard-library mocks. Optional Lua checks
load configuration into an isolated interpreter with no standard libraries;
private configuration values are never printed. Runtime item transfers still
need in-game verification.
"""

import ctypes
import ctypes.util
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def capacity_condition(source, owner):
    pattern = r"if \(([^\n]*" + owner + r"->getMaximumNumberOfPlayerItems\(\)[^\n]*)\) \{"
    matches = re.findall(pattern, source)
    assert len(matches) == 1, "Expected one storage comparison for " + owner
    return matches[0]


MOCKS = r'''
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <map>
#include <string>
using uint8 = uint8_t;
using uint32 = uint32_t;
using int64 = int64_t;
struct ConfigManager {
    std::map<std::string, int> values;
    static ConfigManager* instance() { static ConfigManager value; return &value; }
    int getInt(const std::string& key, int fallback) const {
        auto found = values.find(key);
        return found == values.end() ? fallback : found->second;
    }
};
struct SharedObjectTemplate { virtual ~SharedObjectTemplate() {} };
struct SharedStructureObjectTemplate: SharedObjectTemplate {
    uint8 lots;
    explicit SharedStructureObjectTemplate(uint8 lots): lots(lots) {}
    uint8 getLotSize() const { return lots; }
};
struct StructureObjectImplementation {
    struct TemplateReference {
        SharedObjectTemplate* value;
        SharedObjectTemplate* get() const { return value; }
    } templateObject;
    int additionalLots = 0;
    explicit StructureObjectImplementation(SharedObjectTemplate* value): templateObject{value} {}
    int getBaseLotSize() const;
    int getLotSize() const;
};
struct BuildingObjectImplementation: StructureObjectImplementation {
    int currentItems = 0;
    bool staticBuilding = false;
    explicit BuildingObjectImplementation(SharedObjectTemplate* value): StructureObjectImplementation(value) {}
    int getCurrentNumberOfPlayerItems() const { return currentItems; }
    bool isStaticBuilding() const { return staticBuilding; }
    uint32 getMaximumNumberOfPlayerItems();
};
LOT_METHODS
CAPACITY_METHOD
bool floorRejects(BuildingObjectImplementation* strongParent, int count) {
    return FLOOR_CONDITION;
}
bool nestedRejects(BuildingObjectImplementation* building, int objectSize) {
    return NESTED_CONDITION;
}
int checks = 0;
void check(bool passed, const char* description) {
    ++checks;
    if (!passed) { std::cerr << "Failed: " << description << '\n'; std::exit(1); }
}
int main() {
    auto& settings = ConfigManager::instance()->values;
    const char* perLot = "Core3.StructureManager.ItemsPerLot";
    const char* noLot = "Core3.StructureManager.NoLotItemCount";
    const char* characterLots = "Core3.StructureManager.LotsPerCharacter";
    const int maximum = std::numeric_limits<int>::max();
    SharedStructureObjectTemplate objectTemplate(0);
    BuildingObjectImplementation building(&objectTemplate);
    struct CapacityCase { uint8 lots; uint32 expected; };
    const CapacityCase defaults[] = {{0, 1000}, {1, 200}, {2, 400}, {5, 1000}, {10, 2000}, {255, 51000}};
    for (const auto& item: defaults) {
        objectTemplate.lots = item.lots;
        check(building.getMaximumNumberOfPlayerItems() == item.expected, "unchanged default storage allowance");
    }
    BuildingObjectImplementation missing(nullptr);
    check(missing.getMaximumNumberOfPlayerItems() == 0, "missing template has no storage");
    missing.additionalLots = 3;
    check(missing.getMaximumNumberOfPlayerItems() == 0, "missing template cannot gain storage from saved additional lots");
    SharedObjectTemplate nonStructure;
    BuildingObjectImplementation wrongTemplate(&nonStructure);
    check(wrongTemplate.getMaximumNumberOfPlayerItems() == 0, "non-structure template has no storage");

    objectTemplate.lots = 2;
    building.additionalLots = 3;
    check(building.getBaseLotSize() == 2 && building.getLotSize() == 5, "purchased lots increase total without changing template base");
    check(building.getMaximumNumberOfPlayerItems() == 1000, "purchased lots immediately increase storage");
    building.additionalLots = 254;
    check(building.getLotSize() == 256 && building.getMaximumNumberOfPlayerItems() == 51200,
          "purchased total crossing 255 does not truncate to a byte");
    building.additionalLots = 300;
    check(building.getLotSize() == 302 && building.getMaximumNumberOfPlayerItems() == 60400,
          "larger purchased totals retain their complete storage allowance");
    building.additionalLots = 1;
    check(building.getMaximumNumberOfPlayerItems() == 600, "removing purchased lots immediately lowers storage");
    building.additionalLots = 0;
    check(building.getLotSize() == 2 && building.getMaximumNumberOfPlayerItems() == 400,
          "removing all purchased lots preserves base storage");
    objectTemplate.lots = 0;
    check(building.getMaximumNumberOfPlayerItems() == 1000, "zero-lot building retains its fixed allowance");
    objectTemplate.lots = 2;
    building.additionalLots = maximum - 2;
    settings[perLot] = 1;
    check(building.getLotSize() == maximum && building.getMaximumNumberOfPlayerItems() == static_cast<uint32>(maximum),
          "maximum purchased total is preserved without truncation");
    settings[perLot] = maximum;
    check(building.getMaximumNumberOfPlayerItems() == static_cast<uint32>(maximum),
          "maximum purchased total times maximum items saturates without int64 overflow");
    building.additionalLots = 0;

    settings[perLot] = 80;
    settings[noLot] = 2500;
    const CapacityCase custom[] = {{0, 2500}, {1, 80}, {5, 400}, {255, 20400}};
    for (const auto& item: custom) {
        objectTemplate.lots = item.lots;
        check(building.getMaximumNumberOfPlayerItems() == item.expected, "custom storage uses the building's own lot cost");
    }
    settings[characterLots] = 500;
    check(building.getMaximumNumberOfPlayerItems() == 20400, "account lot allowance does not change building storage");
    objectTemplate.lots = 5;
    settings[perLot] = 240;
    check(building.getMaximumNumberOfPlayerItems() == 1200, "updated storage setting is read by existing building");

    for (int invalid: {0, -1, std::numeric_limits<int>::min()}) {
        settings[perLot] = invalid;
        check(building.getMaximumNumberOfPlayerItems() == 0, "nonpositive per-lot setting clamps to zero");
        objectTemplate.lots = 0;
        check(building.getMaximumNumberOfPlayerItems() == 2500, "per-lot setting does not control zero-lot storage");
        settings[perLot] = 240;
        settings[noLot] = invalid;
        check(building.getMaximumNumberOfPlayerItems() == 0, "nonpositive zero-lot setting clamps to zero");
        objectTemplate.lots = 5;
        check(building.getMaximumNumberOfPlayerItems() == 1200, "zero-lot setting does not control lot-based storage");
        settings[noLot] = 2500;
    }

    settings[perLot] = maximum;
    for (uint8 lots: {1, 2, 255}) {
        objectTemplate.lots = lots;
        check(building.getMaximumNumberOfPlayerItems() == static_cast<uint32>(maximum), "large products saturate at signed counter maximum");
    }
    objectTemplate.lots = 255;
    settings[perLot] = 8421504;
    check(building.getMaximumNumberOfPlayerItems() == 2147483520u, "largest unsaturated 255-lot multiple is exact");
    settings[perLot] = 8421505;
    check(building.getMaximumNumberOfPlayerItems() == static_cast<uint32>(maximum), "next 255-lot multiple saturates without wrapping");
    settings[perLot] = 1000000;
    check(building.getMaximumNumberOfPlayerItems() == 255000000u, "large representable multiplication remains exact");
    settings[noLot] = maximum;
    objectTemplate.lots = 0;
    check(building.getMaximumNumberOfPlayerItems() == static_cast<uint32>(maximum), "maximum zero-lot setting is supported");

    objectTemplate.lots = 5;
    settings[perLot] = 10;
    building.currentItems = 49;
    check(!floorRejects(&building, 1), "floor placement reaching capacity is allowed");
    check(floorRejects(&building, 2), "floor placement exceeding capacity is rejected");
    check(!nestedRejects(&building, 1), "nested insertion reaching capacity is allowed");
    check(nestedRejects(&building, 2), "nested insertion exceeding capacity is rejected");
    building.currentItems = 48;
    check(!floorRejects(&building, 2) && floorRejects(&building, 3), "container contents count toward floor capacity");
    building.currentItems = 50;
    check(!floorRejects(&building, 0), "existing zero-count vendor exception is preserved");
    check(floorRejects(&building, 1), "full building rejects another floor item");
    check(nestedRejects(&building, 1), "full building rejects another nested item");
    building.staticBuilding = true;
    check(!nestedRejects(&building, 1), "existing static-building nested-storage exception is preserved");
    building.staticBuilding = false;
    settings[perLot] = 0;
    building.currentItems = 0;
    check(floorRejects(&building, 1) && nestedRejects(&building, 1), "zero storage rejects new counted items through both paths");
    check(!floorRejects(&building, 0), "zero storage preserves existing uncounted-item behavior");

    settings[perLot] = maximum;
    building.currentItems = maximum - 1;
    check(!floorRejects(&building, 1) && !nestedRejects(&building, 1), "last slot at saturated capacity remains available");
    check(floorRejects(&building, 2), "floor addition above INT_MAX rejects without signed overflow");
    check(nestedRejects(&building, 2), "nested addition above INT_MAX rejects without signed overflow");
    building.currentItems = maximum;
    check(floorRejects(&building, maximum) && nestedRejects(&building, maximum), "two maximum counters cannot wrap to an allowed insertion");
    std::cout << checks << " structure storage arithmetic checks passed\n";
}
'''


def check_configs():
    library = next((name for version in ("lua5.4", "lua5.3", "lua5.2")
                    if (name := ctypes.util.find_library(version))), None)
    if library is None:
        print("Lua configuration checks skipped: no compatible shared library available")
        return
    lua = ctypes.CDLL(library)
    declarations = {
        "luaL_newstate": ([], ctypes.c_void_p),
        "luaL_loadfilex": ([ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
        "lua_pcallk": ([ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p], ctypes.c_int),
        "lua_getglobal": ([ctypes.c_void_p, ctypes.c_char_p], ctypes.c_int),
        "lua_getfield": ([ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p], ctypes.c_int),
        "lua_type": ([ctypes.c_void_p, ctypes.c_int], ctypes.c_int),
        "lua_tointegerx": ([ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)], ctypes.c_longlong),
        "lua_tonumberx": ([ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)], ctypes.c_double),
        "lua_settop": ([ctypes.c_void_p, ctypes.c_int], None),
        "lua_close": ([ctypes.c_void_p], None),
    }
    for name, (arguments, result) in declarations.items():
        method = getattr(lua, name)
        method.argtypes, method.restype = arguments, result
    defaults = {"ItemsPerLot": 200, "NoLotItemCount": 1000, "LotsPerCharacter": 10}
    checks = 0
    for filename in ("config.lua", "config-local.lua"):
        path = CORE / "bin/conf" / filename
        if filename == "config-local.lua" and not path.exists():
            continue
        state = lua.luaL_newstate()
        assert state, "Unable to allocate isolated Lua state"
        try:
            assert lua.luaL_loadfilex(state, os.fsencode(path), None) == 0, filename + " failed Lua syntax validation"
            assert lua.lua_pcallk(state, 0, 0, 0, 0, None) == 0, filename + " failed isolated configuration evaluation"
            checks += 2
            lua.lua_getglobal(state, b"Core3")
            assert lua.lua_type(state, -1) == 5, filename + " lacks Core3 table"
            lua.lua_getfield(state, -1, b"StructureManager")
            assert lua.lua_type(state, -1) == 5, filename + " lacks StructureManager table"
            checks += 2
            for key, default in defaults.items():
                lua.lua_getfield(state, -1, key.encode())
                is_integer = ctypes.c_int()
                value = lua.lua_tointegerx(state, -1, ctypes.byref(is_integer))
                number = lua.lua_tonumberx(state, -1, None)
                assert lua.lua_type(state, -1) == 3 and is_integer.value and number == value, filename + " requires an integer for " + key
                assert -(2**31) <= value <= 2**31 - 1, filename + " exceeds source integer range for " + key
                if filename == "config.lua":
                    assert value == default, filename + " changed the documented default for " + key
                checks += 1
                lua.lua_settop(state, -2)
        finally:
            lua.lua_close(state)
    print(str(checks) + " Lua configuration checks passed (private values omitted)")


def main():
    building = (CORE / "src/server/zone/objects/building/BuildingObjectImplementation.cpp").read_text()
    structure = (CORE / "src/server/zone/objects/structure/StructureObjectImplementation.cpp").read_text()
    cell = (CORE / "src/server/zone/objects/cell/CellObjectImplementation.cpp").read_text()
    container = (CORE / "src/server/zone/objects/tangible/ContainerImplementation.cpp").read_text()
    manager = (CORE / "src/server/zone/managers/structure/StructureManager.cpp").read_text()
    cell_method = function(cell, "int CellObjectImplementation::canAddObject(")
    container_method = function(container, "int ContainerImplementation::canAddObject(")
    floor_condition = capacity_condition(cell_method, "strongParent")
    nested_condition = capacity_condition(container_method, "building")
    assert "static_cast<int64>(strongParent->getCurrentNumberOfPlayerItems())" in floor_condition
    assert "static_cast<int64>(building->getCurrentNumberOfPlayerItems())" in nested_condition
    assert "getCountableObjectsRecursive()" in cell_method and "TOOMANYITEMSINHOUSE" in cell_method
    assert "getContainerObjectsSize() + 1" in container_method and "TOOMANYITEMSINHOUSE" in container_method
    report = function(manager, "void StructureManager::reportStructureStatus(")
    assert re.search(r'Storage Used:[^\n]*getCurrentNumberOfPlayerItems\(\)[^\n]*getMaximumNumberOfPlayerItems\(\)', report)
    account_capacity = function(manager, "int StructureManager::getMaximumAccountLots(")
    assert 'getInt("Core3.StructureManager.LotsPerCharacter", 10)' in account_capacity
    print("6 storage integration source checks passed")
    source = MOCKS.replace("CAPACITY_METHOD", function(building, "uint32 BuildingObjectImplementation::getMaximumNumberOfPlayerItems("))
    lot_methods = "\n".join(function(structure, signature) for signature in (
        "int StructureObjectImplementation::getBaseLotSize(", "int StructureObjectImplementation::getLotSize("))
    source = source.replace("LOT_METHODS", lot_methods)
    source = source.replace("FLOOR_CONDITION", floor_condition).replace("NESTED_CONDITION", nested_condition)
    with tempfile.TemporaryDirectory(prefix=".structure-storage-config-", dir=CORE / "bin") as directory:
        directory = Path(directory)
        cpp, executable = directory / "test.cpp", directory / "test"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic-errors",
                                   "-fsanitize=undefined", "-fno-sanitize-recover=undefined",
                                   str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
    check_configs()


if __name__ == "__main__":
    main()
