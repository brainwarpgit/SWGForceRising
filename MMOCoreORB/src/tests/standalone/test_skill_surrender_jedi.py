#!/usr/bin/env python3
"""Exercise production Jedi surrender preflight using an installed Lua library.

Run with Python 3 and the Lua 5.3 or 5.4 shared library. This loads the two
production Lua manager scripts with mock engine endpoints. It checks projected
progression restrictions against the existing sequential single-skill rules,
without compiling or running Core3 or reading engine3. No files are generated.

These checks cover the Lua hooks, not C++/Lua argument binding, actual skill
data, callbacks, persistence, or runtime gameplay. Builds and in-game tests
remain necessary.
"""

import ctypes
import ctypes.util
from pathlib import Path


CORE_ROOT = Path(__file__).resolve().parents[3]
LUA_ROOT = CORE_ROOT / "bin/scripts/managers/jedi"

SETUP = r'''
ScreenPlay = {}
function ScreenPlay:new(object)
    setmetatable(object, {__index = self})
    return object
end
function require(name)
    if name == "managers.jedi.jedi_manager" then return JediManager end
    if name == "screenplays.screenplay" then return ScreenPlay end
    return {}
end
function registerScreenPlay(...) end
'''

CASES = r'''
local current
function LuaSkillManager()
    return {getSkill = function(self, name)
        local points = current.skills[name]
        if points == nil then return nil end
        return {getSkillPointsRequired = function() return points end}
    end}
end
function LuaSkill(skill) return skill end
function CreatureObject(player) return player end
local function matches(name, part)
    return name:find(part, 1, true) ~= nil
end
local function countedDiscipline(name)
    return matches(name, "force_discipline_") and
        (matches(name, "0") or matches(name, "novice") or matches(name, "master"))
end

-- Mock the read-only CreatureObject endpoints used by the production single-
-- skill rule. Their count semantics match SkillManager's existing C++ helpers.
local function player(skills)
    return {
        skills = skills,
        messages = 0,
        hasSkill = function(self, name) return self.skills[name] ~= nil end,
        sendSystemMessage = function(self) self.messages = self.messages + 1 end,
        getForceSensitiveSkillCount = function(self)
            local count = 0
            for name in pairs(self.skills) do
                if matches(name, "force_sensitive") and matches(name, "0") then
                    count = count + 1
                end
            end
            return count
        end,
        villageKnightPrereqsMet = function(self, drop)
            local points, trees = 0, 0
            for name, cost in pairs(self.skills) do
                if countedDiscipline(name) then
                    points = points + cost
                    if matches(name, "4") then trees = trees + 1 end
                end
            end
            if drop ~= "" then
                points = points - self.skills[drop]
                if matches(drop, "4") then trees = trees - 1 end
            end
            return points >= 206 and trees >= 2
        end,
    }
end
local function copy(skills)
    local result = {}
    for name, cost in pairs(skills) do result[name] = cost end
    return result
end

local tests = 0
local function check(label, skills, plan, expected)
    current = player(copy(skills))
    local owned = {}
    for name in pairs(skills) do table.insert(owned, name) end
    local result = VillageJediManager:canSurrenderSkills(
        current, table.concat(plan, " "), table.concat(owned, " "))
    assert(result == expected, label .. ": unexpected preflight result")
    assert(current.messages == 0, label .. ": preflight emitted messages")
    for name, cost in pairs(skills) do
        assert(current.skills[name] == cost, label .. ": preflight mutated skills")
    end
    for name in pairs(current.skills) do
        assert(skills[name] ~= nil, label .. ": preflight added skills")
    end

    -- Compare the batch decision with actual production single-skill checks
    -- on a separate fixture whose ownership changes after each accepted step.
    local sequentialPlayer = player(copy(skills))
    local sequentialResult = true
    for _, name in ipairs(plan) do
        if not sequentialPlayer:hasSkill(name) or
            (name:find("force_", 1, true) == 1 and
             not VillageJediManager:canSurrenderSkill(sequentialPlayer, name)) then
            sequentialResult = false
            break
        end
        sequentialPlayer.skills[name] = nil
    end
    assert(result == sequentialResult, label .. ": differs from existing sequential rules")
    tests = tests + 1
end

check("ordinary profession", {
    social_entertainer_novice = 15, social_entertainer_dance_01 = 2,
}, {"social_entertainer_dance_01", "social_entertainer_novice"}, true)
check("protected Jedi novice", {force_title_jedi_novice = 0},
    {"force_title_jedi_novice"}, false)
check("protected Jedi rank 02", {force_title_jedi_rank_02 = 0},
    {"force_title_jedi_rank_02"}, false)

local function forceSensitive(count)
    local skills = {
        force_title_jedi_rank_02 = 0,
        force_sensitive_test_novice = 0,
        force_sensitive_test_master = 0,
    }
    for i = 1, count do skills["force_sensitive_test_" .. i .. "_01"] = 1 end
    return skills
end
check("FS retains exactly 24", forceSensitive(26),
    {"force_sensitive_test_1_01", "force_sensitive_test_2_01"}, true)
check("FS cumulative floor failure", forceSensitive(26),
    {"force_sensitive_test_1_01", "force_sensitive_test_2_01", "force_sensitive_test_3_01"}, false)
check("FS novice at floor", forceSensitive(24), {"force_sensitive_test_novice"}, false)
check("FS novice after last allowed tier", forceSensitive(25),
    {"force_sensitive_test_1_01", "force_sensitive_test_novice"}, false)
check("FS novice before last allowed tier", forceSensitive(25),
    {"force_sensitive_test_novice", "force_sensitive_test_1_01"}, true)
check("FS master at floor", forceSensitive(24), {"force_sensitive_test_master"}, false)
local unrestricted = forceSensitive(2)
unrestricted.force_title_jedi_rank_02 = nil
check("FS without rank 02", unrestricted,
    {"force_sensitive_test_1_01", "force_sensitive_test_2_01", "force_sensitive_test_novice"}, true)

local jedi = {
    force_title_jedi_rank_03 = 0,
    force_discipline_a_04 = 100, force_discipline_b_04 = 100,
    force_discipline_c_04 = 6,
    force_discipline_d_01 = 10, force_discipline_e_01 = 10,
}
check("Jedi retains exactly 206 points", jedi,
    {"force_discipline_d_01", "force_discipline_e_01"}, true)
check("Jedi cumulative point failure", jedi,
    {"force_discipline_d_01", "force_discipline_e_01", "force_discipline_c_04"}, false)
local trees = {
    force_title_jedi_rank_03 = 0,
    force_discipline_a_04 = 1, force_discipline_b_04 = 1, force_discipline_c_04 = 1,
    force_discipline_d_01 = 300,
}
check("Jedi retains two complete trees", trees, {"force_discipline_a_04"}, true)
check("Jedi cumulative tree failure", trees,
    {"force_discipline_a_04", "force_discipline_b_04"}, false)
check("duplicate rejected", {social_entertainer_novice = 15},
    {"social_entertainer_novice", "social_entertainer_novice"}, false)
check("unknown rejected", {social_entertainer_novice = 15}, {"missing"}, false)

current = player({force_a = 1, force_b = 1})
assert(JediManager:canSurrenderSkills(current, "force_a force_b", ""))
tests = tests + 1
local custom = JediManager:new({canSurrenderSkill = function() return true end})
assert(not custom:canSurrenderSkills(current, "force_a force_b", ""))
tests = tests + 1
assert(custom:canSurrenderSkills(current, "force_a", ""))
tests = tests + 1
assert(custom:canSurrenderSkills(current, "social_entertainer_novice", ""))
tests = tests + 1
assert(not VillageJediManager:canSurrenderSkills(nil, "", ""))
tests = tests + 1
print(tests .. " standalone Jedi surrender checks passed")
'''


def main():
    library = ctypes.util.find_library("lua5.3") or ctypes.util.find_library("lua5.4")
    if not library:
        raise SystemExit("A Lua 5.3 or 5.4 shared library is required for these checks.")

    lua = ctypes.CDLL(library)
    lua.luaL_newstate.restype = ctypes.c_void_p
    lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.lua_pcallk.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_ssize_t, ctypes.c_void_p,
    ]
    lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
    lua.lua_tolstring.restype = ctypes.c_char_p
    lua.lua_close.argtypes = [ctypes.c_void_p]

    state = lua.luaL_newstate()
    if not state:
        raise SystemExit("Could not create the standalone Lua state.")
    lua.luaL_openlibs(state)

    def run(source):
        result = lua.luaL_loadstring(state, source.encode())
        if result == 0:
            result = lua.lua_pcallk(state, 0, 0, 0, 0, None)
        if result != 0:
            message = lua.lua_tolstring(state, -1, None)
            raise RuntimeError(message.decode() if message else "Unknown Lua error")

    try:
        run(SETUP)
        for filename in ("jedi_manager.lua", "village_jedi_manager.lua"):
            run((LUA_ROOT / filename).read_text())
        run(CASES)
    finally:
        lua.lua_close(state)


if __name__ == "__main__":
    main()
