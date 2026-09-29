#!/usr/bin/env python3
"""Exercise the actual account-lot initializer against fake persisted records.

Extracts initializeAccountLots from StructureManager.cpp and compiles it with
the real scalar ledger, stdlib database/serialization fixtures, and template
mocks. No Core3 or engine3 component is built or run, and no live database is
opened. Temporary files stay under MMOCoreORB/bin. Actual saved-data decoding,
startup ordering, and world ownership changes still need integration testing.
"""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]
SOURCE = CORE / "src/server/zone/managers/structure/StructureManager.cpp"
HEADER = CORE / "src/server/zone/managers/structure/AccountLotLedger.h"

MOCKS = r'''
#include "AccountLotLedger.h"
#include <any>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using uint64 = std::uint64_t;
using uint32 = std::uint32_t;
using uint8 = std::uint8_t;
using int64 = std::int64_t;
using String = std::string;
#define STRING_HASHCODE(value) value

template<class K, class V> struct VectorMap {
    std::map<K, V> values;
    bool contains(const K& key) const { return values.count(key) != 0; }
    V get(const K& key) const {
        auto found = values.find(key);
        return found == values.end() ? V{} : found->second;
    }
    void put(const K& key, const V& value) { values[key] = value; }
};

struct Exception : std::runtime_error {
    using std::runtime_error::runtime_error;
    const char* getMessage() const { return what(); }
};
using Record = std::map<String, std::any>;
struct ObjectInputStream {
    Record record;
    explicit ObjectInputStream(int) {}
    void clear() { record.clear(); }
};
struct Serializable {
    template<class T> static bool getVariable(const char* field, T* value, ObjectInputStream* data) {
        auto entry = data->record.find(field);
        if (entry == data->record.end()) return false;
        auto typed = std::any_cast<T>(&entry->second);
        if (typed == nullptr) return false;
        *value = *typed;
        return true;
    }
};
struct ObjectDatabase {
    std::map<uint64, Record> rows;
    std::set<uint64> unreadable;
    bool iteratorThrows = false;
    int getData(uint64 id, ObjectInputStream* data) const {
        auto row = rows.find(id);
        if (row == rows.end() || unreadable.count(id) != 0) return 1;
        data->record = row->second;
        return 0;
    }
};
struct ObjectDatabaseIterator {
    ObjectDatabase* database;
    std::map<uint64, Record>::const_iterator cursor;
    explicit ObjectDatabaseIterator(ObjectDatabase* value) : database(value), cursor(value->rows.begin()) {}
    bool getNextKeyAndValue(uint64& id, ObjectInputStream* data) {
        if (database->iteratorThrows) throw Exception("fixture iterator read failed");
        if (cursor == database->rows.end()) return false;
        id = cursor->first;
        data->record = cursor->second;
        ++cursor;
        return true;
    }
};
struct ObjectDatabaseManager {
    ObjectDatabase scene, structures;
    bool missingScene = false, missingStructures = false;
    static ObjectDatabaseManager*& current() { static ObjectDatabaseManager* value = nullptr; return value; }
    static ObjectDatabaseManager* instance() { return current(); }
    ObjectDatabase* loadObjectDatabase(const String& name, bool) {
        if (name == "sceneobjects") return missingScene ? nullptr : &scene;
        if (name == "playerstructures") return missingStructures ? nullptr : &structures;
        throw Exception("unexpected fixture database");
    }
};

struct SharedObjectTemplate { virtual ~SharedObjectTemplate() = default; };
struct SharedStructureObjectTemplate : SharedObjectTemplate {
    int lots;
    explicit SharedStructureObjectTemplate(int value) : lots(value) {}
    int getLotSize() const { return lots; }
};
struct TemplateManager {
    std::map<uint32, SharedObjectTemplate*> templates;
    SharedObjectTemplate* getTemplate(uint32 crc) const {
        auto found = templates.find(crc);
        return found == templates.end() ? nullptr : found->second;
    }
};
struct LogSink {
    template<class T> LogSink& operator<<(const T&) { return *this; }
};
struct StructureManager {
    AccountLotLedger accountLots;
    std::map<uint32, int> legacyLotBonuses;
    TemplateManager* templateManager;
    int errors = 0;
    explicit StructureManager(TemplateManager* templates) : templateManager(templates) {}
    LogSink info(bool) { return {}; }
    LogSink error() { ++errors; return {}; }
    void error(const char*) { ++errors; }
    void initializeAccountLots();
};
'''

CASES = r'''
int checks = 0;
void check(bool result, const char* description) {
    if (!result) {
        std::cerr << "FAIL: " << description << '\n';
        std::exit(1);
    }
    ++checks;
}

struct Fixture {
    ObjectDatabaseManager db;
    TemplateManager templates;
    SharedStructureObjectTemplate zero{0}, two{2}, three{3}, four{4}, five{5}, six{6}, negative{-1};
    SharedObjectTemplate notStructure;
    StructureManager manager{&templates};
    Fixture() {
        ObjectDatabaseManager::current() = &db;
        templates.templates = {{10, &zero}, {12, &two}, {13, &three}, {14, &four},
                               {15, &five}, {16, &six}, {17, &negative}, {18, &notStructure}};
    }
    void player(uint64 owner, uint64 ghost, uint32 account, int legacyMaximum = 10) {
        VectorMap<String, uint64> slots;
        slots.put("ghost", ghost);
        db.scene.rows[owner] = {{"SceneObject.slottedObjects", slots}};
        auto& record = db.scene.rows[ghost];
        record = {{"PlayerObject.accountID", account}, {"TreeEntry.parent", owner}};
        if (legacyMaximum >= 0) record["PlayerObject.maximumLots"] = static_cast<uint8>(legacyMaximum);
    }
    void structure(uint64 id, uint64 owner, uint32 crc = 12, bool scene = false) {
        auto& table = scene ? db.scene : db.structures;
        table.rows[id] = {{"StructureObject.ownerObjectID", owner}, {"SceneObject.serverObjectCRC", crc}};
    }
    void run() { manager.initializeAccountLots(); }
    void rejected(const char* label) {
        run();
        check(!manager.accountLots.isReady(), label);
        check(manager.errors == 1, "bootstrap failure is reported");
        check(manager.accountLots.remaining(1, 100) == 0, "partial bootstrap grants no remaining lots");
        check(manager.accountLots.reserve(1, 100, 1) == 0, "partial bootstrap cannot reserve lots");
    }
};

void completeSavedRoster() {
    Fixture f;
    f.player(11, 101, 1, 15);
    f.player(12, 102, 1, 7);
    f.player(13, 103, 1, -1); // Older ghost missing maximumLots defaults to ten.
    f.player(21, 104, 2, 8);
    // Roster/login flags deliberately have no role in the persisted ownership scan.
    f.db.scene.rows[102]["fixtureBanned"] = true;
    f.db.scene.rows[103]["fixturePendingDeletion"] = true;
    f.db.scene.rows[101]["PlayerObject.ownedStructures"] = std::vector<uint64>{999, 300};
    f.structure(201, 11, 12);
    f.structure(202, 12, 15);
    f.structure(203, 13, 13);
    f.db.structures.rows[203]["SceneObject.zone"] = String("disabled_planet");
    f.structure(204, 13, 14, true);
    f.structure(204, 13, 14); // Same ID encountered twice must not double charge.
    f.structure(300, 21, 16);
    f.structure(301, 0, 999); // Unowned object needs neither owner nor template resolution.
    f.structure(302, 900, 10); // Zero-lot child may have no player owner.
    f.db.scene.rows[901] = {{"SceneObject.slottedObjects", VectorMap<String, uint64>{}}};
    f.structure(303, 901, 15); // Proven non-player owner is exempt.
    f.run();
    check(f.manager.accountLots.isReady(), "complete offline roster bootstrap succeeds");
    check(f.manager.errors == 0, "valid saved records produce no bootstrap error");
    check(f.manager.accountLots.remaining(1, 100) == 86,
          "offline/banned/deleted, disabled-zone and sceneobjects structures are all counted once");
    check(f.manager.accountLots.remaining(2, 100) == 94,
          "actual structure owner overrides a stale ownedStructures claim by another character");
    check(f.manager.legacyLotBonuses.at(1) == 2, "sibling legacy bonuses sum signed deltas from ten");
    check(f.manager.legacyLotBonuses.at(2) == -2, "legacy allowances remain account-specific");
    auto token = f.manager.accountLots.reserve(1, 100, 86);
    check(token != 0, "bootstrapped exact remaining capacity is usable");
    check(f.manager.accountLots.reserve(1, 100, 1) == 0, "bootstrapped ownership prevents overspending");
    f.manager.accountLots.release(token);
    check(f.manager.accountLots.remaining(1, 100) == 86, "cancelling reservation preserves saved usage");
}

void invalidSavedRecords() {
    { Fixture f; f.db.missingScene = true; f.rejected("missing scene database fails closed"); }
    { Fixture f; f.db.missingStructures = true; f.rejected("missing structures database fails closed"); }
    { Fixture f; f.db.scene.iteratorThrows = true; f.rejected("scene iterator failure fails closed"); }
    { Fixture f; f.db.structures.iteratorThrows = true; f.rejected("structure iterator failure fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.db.scene.rows[101].erase("TreeEntry.parent");
      f.rejected("missing persisted parent fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.db.scene.rows[101]["TreeEntry.parent"] = uint64(0);
      f.rejected("zero persisted parent fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.db.scene.rows[101]["TreeEntry.parent"] = String("11");
      f.rejected("malformed persisted parent fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.player(11, 102, 2);
      f.rejected("conflicting account ownership fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.structure(201, 11); f.structure(202, 99);
      f.rejected("unknown positive-lot owner fails closed after partial population"); }
    { Fixture f; f.structure(202, 99); f.db.scene.rows[99] = {};
      f.rejected("owner without readable slots is not presumed non-player"); }
    { Fixture f; f.structure(202, 99); VectorMap<String, uint64> slots; slots.put("ghost", 199);
      f.db.scene.rows[99] = {{"SceneObject.slottedObjects", slots}};
      f.rejected("owner with unresolved player ghost fails closed"); }
    { Fixture f; f.player(99, 199, 0); f.structure(202, 99);
      f.rejected("player ghost without account cannot evade its lot charge"); }
    { Fixture f; f.db.scene.rows[99] = {{"SceneObject.slottedObjects", VectorMap<String, uint64>{}}};
      f.db.scene.unreadable.insert(99); f.structure(202, 99);
      f.rejected("owner record read failure fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.structure(201, 11);
      f.db.structures.rows[201].erase("SceneObject.serverObjectCRC");
      f.rejected("missing structure template CRC fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.structure(201, 11, 999);
      f.rejected("unavailable structure template fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.structure(201, 11, 18);
      f.rejected("non-structure template fails closed"); }
    { Fixture f; f.player(11, 101, 1); f.structure(201, 11, 17);
      f.rejected("negative player structure lot size fails closed"); }
}

void exclusionsAndDefaults() {
    { Fixture f; f.run();
      check(f.manager.accountLots.isReady() && f.manager.errors == 0, "empty initial world may become ready");
      check(f.manager.accountLots.remaining(1, 100) == 100, "empty world has no lot usage"); }
    { Fixture f; f.player(11, 101, 1, -1); f.run();
      check(f.manager.legacyLotBonuses.at(1) == 0, "missing legacy field does not create an admin bonus"); }
    { Fixture f; VectorMap<String, uint64> slots; slots.put("ghost", 0);
      f.db.scene.rows[99] = {{"SceneObject.slottedObjects", slots}};
      f.structure(202, 99, 15); f.run();
      check(f.manager.accountLots.isReady() && f.manager.errors == 0, "explicit empty ghost is provably non-player");
      check(f.manager.accountLots.remaining(1, 100) == 100, "non-player structure does not charge player accounts"); }
}

int main() {
    completeSavedRoster();
    invalidSavedRecords();
    exclusionsAndDefaults();
    std::cout << "PASS: " << checks << " account lot bootstrap checks\n";
}
'''


def initializer(source):
    signature = "void StructureManager::initializeAccountLots()"
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    with tempfile.TemporaryDirectory(prefix="account-lot-bootstrap-", dir=CORE / "bin") as work:
        directory = Path(work)
        source, executable = directory / "bootstrap.cpp", directory / "bootstrap"
        source.write_text(MOCKS + initializer(SOURCE.read_text()) + CASES)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(
            compiler + ["-std=c++17", "-O2", "-pthread", "-Wall", "-Wextra", "-Werror",
                        "-pedantic", "-I", str(HEADER.parent), str(source), "-o", str(executable)],
            check=True, timeout=60,
        )
        subprocess.run([str(executable)], check=True, timeout=20)


if __name__ == "__main__":
    main()
