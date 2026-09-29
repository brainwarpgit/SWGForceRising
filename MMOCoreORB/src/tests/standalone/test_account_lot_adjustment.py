#!/usr/bin/env python3
"""Exercise account lot bonuses, capacity and the actual admin command body.

Compiles extracted production control flow against standard-library mocks only.
No Core3 component or engine3 header is built. Object-database persistence, IDL
generated locking, and client behavior still require full-server verification.
"""

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


MOCKS = r'''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <map>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
using uint32 = uint32_t;
using uint64 = uint64_t;
using int64 = int64_t;
using Exception = std::runtime_error;
struct String: std::string {
    using std::string::string;
    String() = default;
    String(const std::string& value): std::string(value) {}
    const char* toCharArray() const { return c_str(); }
};
struct UnicodeString: String {
    using String::String;
    String toString() const { return *this; }
};
struct StringBuffer: std::ostringstream {
    String toString() const { return str(); }
};
struct StringTokenizer {
    std::vector<std::string> tokens;
    size_t position = 0;
    explicit StringTokenizer(const String& value) {
        std::istringstream stream(value);
        for (std::string token; stream >> token;) tokens.push_back(token);
    }
    bool hasMoreTokens() const { return position < tokens.size(); }
    void getStringToken(String& output) {
        if (!hasMoreTokens()) throw Exception("No token");
        output = tokens.at(position++);
    }
};
template<class T> struct Ref {
    T value = nullptr;
    Ref() = default;
    Ref(T value): value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
};
template<class T> using ManagedReference = Ref<T>;
template<class T, class U> T cast(U* value) { return static_cast<T>(value); }
struct Lockable { std::recursive_mutex mutex; };
struct Locker {
    std::lock_guard<std::recursive_mutex> lock;
    explicit Locker(Lockable* object): lock(object->mutex) {}
};
template<class K, class V> struct VectorMap {
    std::map<K, V> values;
    bool contains(K key) const { return values.count(key) != 0; }
    V get(K key) const { return values.at(key); }
    void put(K key, V value) { values[key] = value; }
};
struct AccountImplementation: Lockable {
    struct Self {
        AccountImplementation* owner;
        AccountImplementation* getReferenceUnsafeStaticCast() { return owner; }
    } _this{this};
    uint32 id = 77;
    VectorMap<unsigned int, int> structureLotBonuses;
    uint32 getAccountID() const { return id; }
    int getStructureLotBonus(unsigned int galaxyID);
    bool adjustStructureLotBonus(uint32 galaxyID, int delta);
    void initializeStructureLotBonus(uint32 galaxyID, int legacyBonus);
};
using Account = AccountImplementation;
struct ConfigManager {
    int slots = 10;
    std::map<std::string, int> values;
    static ConfigManager* instance() { static ConfigManager config; return &config; }
    void setLotsPerCharacter(int value) { values["Core3.StructureManager.LotsPerCharacter"] = value; }
    int getInt(const char* key, int fallback) const {
        assert(fallback == 10);
        if (std::string(key) == "Core3.PlayerCreationManager.MaxCharactersPerGalaxy") return slots;
        assert(std::string(key) == "Core3.StructureManager.LotsPerCharacter");
        auto found = values.find(key);
        return found == values.end() ? fallback : found->second;
    }
};
struct PlayerObject;
struct SceneObject {
    virtual ~SceneObject() = default;
    virtual bool isPlayerCreature() const { return false; }
};
struct ZoneServer {
    uint32 galaxyID = 1;
    std::map<uint64, SceneObject*> objects;
    uint32 getGalaxyID() const { return galaxyID; }
    SceneObject* getObject(uint64 id) const {
        auto found = objects.find(id);
        return found == objects.end() ? nullptr : found->second;
    }
};
struct StructureManager {
    inline static StructureManager* current = nullptr;
    static StructureManager* instance() { return current; }
    struct Ledger {
        bool ready = true;
        bool isReady() const { return ready; }
    } accountLots;
    ZoneServer* server = nullptr;
    std::map<uint32, int> legacyLotBonuses;
    bool isAccountLotsReady() const { return accountLots.isReady(); }
    int getMaximumAccountLots(PlayerObject* player);
};
struct PlayerObject {
    Account* account = nullptr;
    StructureManager* manager = nullptr;
    uint32 accountID = 77;
    int capacityReads = 0;
    Account* getAccount() const { return account; }
    uint32 getAccountID() const { return accountID; }
    int getMaximumLots() {
        ++capacityReads;
        return manager->getMaximumAccountLots(this);
    }
};
struct CreatureObject: SceneObject {
    ZoneServer* server = nullptr;
    PlayerObject* ghost = nullptr;
    bool player = true;
    std::vector<String> messages;
    ZoneServer* getZoneServer() const { return server; }
    PlayerObject* getPlayerObject() const { return ghost; }
    bool isPlayerCreature() const override { return player; }
    String getFirstName() const { return "Target"; }
    void sendSystemMessage(const String& message) { messages.push_back(message); }
};
enum { SUCCESS, INVALIDSTATE, INVALIDLOCOMOTION, INVALIDTARGET, INVALIDPARAMETERS, GENERALERROR };
struct AdjustLotCountCommand {
    bool stateAllowed = true, locomotionAllowed = true;
    bool checkStateMask(CreatureObject*) const { return stateAllowed; }
    bool checkInvalidLocomotions(CreatureObject*) const { return locomotionAllowed; }
    // The command method is inserted below verbatim.
    COMMAND_METHOD
};
struct Fixture {
    Account account, otherAccount;
    ZoneServer server;
    StructureManager manager;
    PlayerObject ghost, altGhost;
    CreatureObject admin, target;
    AdjustLotCountCommand command;
    Fixture() {
        ConfigManager::instance()->slots = 10;
        ConfigManager::instance()->values.clear();
        StructureManager::current = &manager;
        manager.server = &server;
        ghost.account = altGhost.account = &account;
        ghost.manager = altGhost.manager = &manager;
        admin.server = target.server = &server;
        target.ghost = &ghost;
        server.objects[9] = &target;
        otherAccount.id = 88;
    }
    int execute(const char* text) { return command.doQueueCommand(&admin, 9, UnicodeString(text)); }
};
'''


CASES = r'''
int main() {
    int checks = 0;
    auto check = [&](bool result, const char* description) {
        if (!result) { std::cerr << "Failed: " << description << '\n'; std::abort(); }
        ++checks;
    };
    const int maximum = std::numeric_limits<int>::max();
    const int minimum = std::numeric_limits<int>::min();
    {
        Account account;
        check(account.getStructureLotBonus(1) == 0, "missing account bonus defaults to zero");
        check(account.structureLotBonuses.values.empty(), "reading missing bonus does not initialize it");
        account.initializeStructureLotBonus(1, 23);
        check(account.getStructureLotBonus(1) == 23, "legacy bonus initializes account");
        account.initializeStructureLotBonus(1, 99);
        check(account.getStructureLotBonus(1) == 23, "repeat migration preserves existing bonus");
        account.initializeStructureLotBonus(2, 0);
        check(account.structureLotBonuses.contains(2), "initialized zero is explicitly recorded");
        account.initializeStructureLotBonus(2, 99);
        check(account.getStructureLotBonus(2) == 0, "repeat migration cannot replace initialized zero");
        check(account.getStructureLotBonus(1) == 23, "galaxy initialization remains isolated");
        check(account.adjustStructureLotBonus(1, 7), "positive bonus adjustment succeeds");
        check(account.getStructureLotBonus(1) == 30, "positive delta adds to migrated bonus");
        check(account.adjustStructureLotBonus(1, -40), "negative bonus adjustment succeeds");
        check(account.getStructureLotBonus(1) == -10, "negative account bonus retained");
        check(account.getStructureLotBonus(2) == 0, "adjustment does not alter other galaxy");
        account.initializeStructureLotBonus(1, 100);
        check(account.getStructureLotBonus(1) == -10, "migration does not overwrite admin changes");
        check(account.adjustStructureLotBonus(3, 5) && account.getStructureLotBonus(3) == 5,
              "adjustment can initialize an absent galaxy");
        check(account.adjustStructureLotBonus(4, 0) && account.structureLotBonuses.contains(4),
              "zero adjustment records initialized zero");
        Account reloaded;
        reloaded.structureLotBonuses.values = account.structureLotBonuses.values;
        reloaded.initializeStructureLotBonus(1, 200);
        reloaded.initializeStructureLotBonus(2, 200);
        check(reloaded.getStructureLotBonus(1) == -10 && reloaded.getStructureLotBonus(2) == 0,
              "loaded bonus map keeps admin values and initialized zero");
    }
    {
        Account account;
        account.initializeStructureLotBonus(1, maximum);
        check(!account.adjustStructureLotBonus(1, 1), "positive overflow rejected");
        check(account.getStructureLotBonus(1) == maximum, "positive overflow leaves bonus unchanged");
        check(account.adjustStructureLotBonus(1, minimum), "opposite signed extremes safely combine");
        check(account.getStructureLotBonus(1) == -1, "extreme addition does not wrap");
        account.initializeStructureLotBonus(2, minimum);
        check(!account.adjustStructureLotBonus(2, -1), "negative overflow rejected");
        check(account.getStructureLotBonus(2) == minimum, "negative overflow leaves bonus unchanged");
        check(account.adjustStructureLotBonus(2, maximum), "large positive adjustment from minimum succeeds");
        check(account.getStructureLotBonus(2) == -1, "minimum plus maximum correct");
        check(account.adjustStructureLotBonus(3, maximum), "maximum delta accepted from zero");
        check(account.adjustStructureLotBonus(4, minimum), "minimum delta accepted from zero");
    }
    {
        Account account;
        std::vector<std::thread> workers;
        for (int i = 0; i < 4; ++i) {
            workers.emplace_back([&] {
                for (int j = 0; j < 1000; ++j) assert(account.adjustStructureLotBonus(1, 1));
            });
        }
        for (auto& worker : workers) worker.join();
        check(account.getStructureLotBonus(1) == 4000, "concurrent adjustments retain every delta with account lock");
    }
    {
        Fixture f;
        check(f.ghost.getMaximumLots() == 100, "default ten character slots provide one hundred lots");
        f.account.adjustStructureLotBonus(1, 15);
        check(f.ghost.getMaximumLots() == 115, "shared maximum includes account bonus");
        check(f.altGhost.getMaximumLots() == 115, "second character sees same account maximum");
        ConfigManager::instance()->slots = 5;
        check(f.ghost.getMaximumLots() == 65, "configuration changes recompute base without losing bonus");
        ConfigManager::instance()->slots = 0;
        check(f.ghost.getMaximumLots() == 15, "zero slots retain only bonus");
        ConfigManager::instance()->slots = -4;
        check(f.ghost.getMaximumLots() == 15, "negative slot setting contributes zero base");
        f.account.adjustStructureLotBonus(1, -30);
        check(f.ghost.getMaximumLots() == 0, "negative total clamps to zero");
        ConfigManager::instance()->slots = maximum;
        check(f.ghost.getMaximumLots() == maximum, "base multiplication clamps instead of overflowing");
        f.server.galaxyID = 2;
        ConfigManager::instance()->slots = 10;
        check(f.ghost.getMaximumLots() == 100, "other galaxy does not inherit bonus");
        f.altGhost.account = &f.otherAccount;
        f.altGhost.accountID = 88;
        check(f.altGhost.getMaximumLots() == 100, "other account does not inherit bonus");
    }
    {
        Fixture f;
        ConfigManager::instance()->setLotsPerCharacter(10);
        check(f.ghost.getMaximumLots() == 100, "explicit ten lots matches the missing-setting default");
    }
    for (const auto& example : std::vector<std::pair<int, int>>{
            {4, 40}, {25, 250}, {0, 0}, {-4, 0}, {minimum, 0}, {maximum, maximum}}) {
        Fixture f;
        ConfigManager::instance()->setLotsPerCharacter(example.first);
        check(f.ghost.getMaximumLots() == example.second, "configured lots per slot recomputes base with safe zero and upper clamps");
        check(f.altGhost.getMaximumLots() == example.second, "configured base remains shared between account characters");
    }
    {
        Fixture f;
        auto config = ConfigManager::instance();
        config->slots = 3;
        config->setLotsPerCharacter(25);
        check(f.ghost.getMaximumLots() == 75, "both configuration factors determine account base");
        f.account.adjustStructureLotBonus(1, 15);
        check(f.ghost.getMaximumLots() == 90, "configured base adds signed account bonus once");
        config->setLotsPerCharacter(0);
        check(f.ghost.getMaximumLots() == 15, "zero lots per character preserves only positive bonus");
        config->setLotsPerCharacter(-7);
        check(f.ghost.getMaximumLots() == 15, "negative lots per character contributes no base");
        config->slots = -3;
        check(f.ghost.getMaximumLots() == 15, "two negative settings cannot produce positive base");
        config->slots = 0;
        config->setLotsPerCharacter(maximum);
        check(f.ghost.getMaximumLots() == 15, "zero slots with maximum lots still contributes no base");
        f.account.adjustStructureLotBonus(1, -30);
        check(f.ghost.getMaximumLots() == 0, "signed bonus still clamps final configured total at zero");
    }
    {
        Fixture f;
        auto config = ConfigManager::instance();
        config->slots = 1;
        config->setLotsPerCharacter(maximum);
        check(f.ghost.getMaximumLots() == maximum, "maximum lots value is representable for one slot");
        config->slots = maximum;
        f.account.adjustStructureLotBonus(1, maximum);
        check(f.ghost.getMaximumLots() == maximum, "two maximum factors plus maximum bonus do not overflow int64");
    }
    {
        Fixture f;
        ConfigManager::instance()->slots = 2;
        ConfigManager::instance()->setLotsPerCharacter(maximum);
        f.account.adjustStructureLotBonus(1, minimum);
        check(f.ghost.getMaximumLots() == maximum - 1, "signed bonus applies before clamping an oversized base");
    }
    {
        Fixture f;
        ConfigManager::instance()->setLotsPerCharacter(4);
        f.manager.legacyLotBonuses[77] = 12;
        check(f.ghost.getMaximumLots() == 52, "nondefault configured base preserves existing legacy bonus total");
        check(f.altGhost.getMaximumLots() == 52 && f.account.getStructureLotBonus(1) == 12,
              "sibling capacity lookup does not migrate legacy bonus twice");
        f.manager.legacyLotBonuses[77] = 99;
        check(f.ghost.getMaximumLots() == 52, "later capacity lookup does not reapply changed legacy sum");
        ConfigManager::instance()->setLotsPerCharacter(20);
        check(f.ghost.getMaximumLots() == 212 && f.account.getStructureLotBonus(1) == 12,
              "changing configured lots never rescales or reapplies migrated bonus");
        f.account.adjustStructureLotBonus(1, -2);
        check(f.altGhost.getMaximumLots() == 210, "other character sees adjusted migrated total with configured base");
    }
    {
        Fixture f;
        check(f.manager.getMaximumAccountLots(nullptr) == 0, "null player has no capacity");
        f.ghost.accountID = 0;
        check(f.ghost.getMaximumLots() == 0, "missing account ID has no capacity");
        f.ghost.accountID = 77;
        f.manager.server = nullptr;
        check(f.ghost.getMaximumLots() == 0, "missing server fails closed");
        f.manager.server = &f.server;
        f.manager.accountLots.ready = false;
        check(f.ghost.getMaximumLots() == 0, "uninitialized lot ledger fails closed");
        f.manager.accountLots.ready = true;
        f.ghost.account = nullptr;
        check(f.ghost.getMaximumLots() == 0, "missing account object fails closed");
        f.ghost.account = &f.otherAccount;
        check(f.ghost.getMaximumLots() == 0, "mismatched account object fails closed");
        check(f.account.structureLotBonuses.values.empty(), "failed capacity checks do not initialize bonus");
    }
    for (const auto* invalid : {"", " ", "words", "+", "-", "1.5", "--1", "1x", "0x10",
                                "1 2", "1 trailing", "+ 1", "2147483648", "-2147483649",
                                "999999999999999999999999999999999999999999999999",
                                "-99999999999999999999999999999999999999999999999"}) {
        Fixture f;
        f.manager.legacyLotBonuses[77] = 20;
        check(f.execute(invalid) == INVALIDPARAMETERS, "invalid admin argument rejected");
        check(f.account.structureLotBonuses.values.empty() && f.ghost.capacityReads == 0,
              "invalid argument does not migrate or modify account");
        check(f.admin.messages.size() == 1 && f.admin.messages[0].find("SYNTAX:") == 0,
              "invalid argument reports syntax once");
    }
    for (const auto& example : std::vector<std::pair<const char*, int>>{
             {"5", 5}, {"+5", 5}, {"-5", -5}, {"0", 0}, {"-0", 0},
             {"  +12  ", 12}, {"0009", 9}, {"2147483647", maximum}, {"-2147483648", minimum}}) {
        Fixture f;
        check(f.execute(example.first) == SUCCESS, "valid signed admin argument accepted");
        check(f.account.getStructureLotBonus(1) == example.second, "valid argument applies exact value");
    }
    {
        Fixture f;
        f.manager.legacyLotBonuses[77] = 20;
        check(f.execute("+5") == SUCCESS, "command succeeds with legacy bonus");
        check(f.account.getStructureLotBonus(1) == 25, "command migrates before adjusting");
        check(f.altGhost.getMaximumLots() == 125, "command affects the account's other character");
        check(f.admin.messages.size() == 1 && f.admin.messages[0].find("Account bonus: 25") != String::npos &&
              f.admin.messages[0].find("total account lots: 125") != String::npos,
              "success message reports shared bonus and total");
        ConfigManager::instance()->setLotsPerCharacter(4);
        check(f.execute("0") == SUCCESS && f.altGhost.getMaximumLots() == 65 && f.account.getStructureLotBonus(1) == 25,
              "admin command uses configured base while preserving account bonus");
        check(f.admin.messages.back().find("total account lots: 65") != String::npos,
              "admin success message reports newly configured total");
        check(f.otherAccount.structureLotBonuses.values.empty(), "command does not modify another account");
        f.account.initializeStructureLotBonus(2, 50);
        check(f.execute("-10") == SUCCESS && f.account.getStructureLotBonus(1) == 15,
              "later command applies relative negative adjustment");
        check(f.account.getStructureLotBonus(2) == 50, "command does not modify another galaxy");
    }
    {
        Fixture f;
        f.account.initializeStructureLotBonus(1, maximum);
        check(f.execute("1") == INVALIDPARAMETERS, "command rejects cumulative positive overflow");
        check(f.account.getStructureLotBonus(1) == maximum, "command overflow preserves prior bonus");
        check(f.admin.messages.back().find("No change was made") != String::npos,
              "cumulative overflow reports no change");
    }
    {
        Fixture f;
        f.account.initializeStructureLotBonus(1, minimum);
        check(f.execute("-1") == INVALIDPARAMETERS, "command rejects cumulative negative overflow");
        check(f.account.getStructureLotBonus(1) == minimum, "negative command overflow preserves bonus");
    }
    {
        Fixture f;
        f.manager.legacyLotBonuses[77] = 20;
        f.manager.accountLots.ready = false;
        check(f.execute("5") == GENERALERROR, "command rejects unready lot ledger");
        check(f.account.structureLotBonuses.values.empty() && f.ghost.capacityReads == 0,
              "unready ledger cannot bypass legacy migration and record an incorrect bonus");
        check(f.admin.messages.size() == 1 && f.admin.messages[0].find("Account lot data is unavailable") == 0,
              "unready ledger reports why adjustment was rejected");
        f.manager.accountLots.ready = true;
        check(f.execute("5") == SUCCESS && f.account.getStructureLotBonus(1) == 25,
              "later valid adjustment retains the full legacy bonus");
    }
    for (uint32 invalidID : {0u, 88u}) {
        Fixture f;
        f.ghost.accountID = invalidID;
        check(f.execute("5") == GENERALERROR, "command rejects missing or mismatched account identity");
        check(f.account.structureLotBonuses.values.empty() && f.ghost.capacityReads == 0,
              "invalid identity cannot change account or run migration");
    }
    {
        Fixture f;
        f.command.stateAllowed = false;
        check(f.execute("1") == INVALIDSTATE, "command honors state mask");
        f.command.stateAllowed = true;
        f.command.locomotionAllowed = false;
        check(f.execute("1") == INVALIDLOCOMOTION, "command honors locomotion restriction");
        f.command.locomotionAllowed = true;
        f.admin.server = nullptr;
        check(f.execute("1") == GENERALERROR, "command rejects missing server");
        f.admin.server = &f.server;
        f.server.objects.clear();
        check(f.execute("1") == INVALIDTARGET, "command rejects missing target");
        f.server.objects[9] = &f.target;
        f.target.player = false;
        check(f.execute("1") == INVALIDTARGET, "command rejects non-player target");
        f.target.player = true;
        f.target.ghost = nullptr;
        check(f.execute("1") == INVALIDPARAMETERS, "command rejects target missing ghost");
        f.target.ghost = &f.ghost;
        f.ghost.account = nullptr;
        check(f.execute("1") == GENERALERROR, "command rejects missing target account");
        check(f.account.structureLotBonuses.values.empty(), "rejected commands leave bonus untouched");
    }
    std::cout << checks << " account lot adjustment/capacity/command checks passed\n";
}
'''


def main():
    account_idl = (CORE / "src/server/login/account/Account.idl").read_text()
    account = (CORE / "src/server/login/account/AccountImplementation.cpp").read_text()
    command = (CORE / "src/server/zone/objects/creature/commands/AdjustLotCountCommand.h").read_text()
    structure = (CORE / "src/server/zone/managers/structure/StructureManager.cpp").read_text()

    # A transient map would silently discard both admin adjustments and the
    # initialized-zero migration marker when accounts are loaded again.
    assert re.search(r"@dereferenced\s+protected VectorMap<unsigned int, int> structureLotBonuses;", account_idl)
    assert re.search(r"@read\s+public synchronized int getStructureLotBonus", account_idl)
    assert "structureLotBonuses" not in function(account, "void AccountImplementation::initializeTransientMembers()")
    bootstrap = function(structure, "void StructureManager::initializeAccountLots()")
    assert re.search(r"uint8\s+previousMaximum\s*=\s*10\s*;", bootstrap)
    assert re.search(r"bonuses\[accountID\]\s*\+=\s*static_cast<int>\(previousMaximum\)\s*-\s*10\s*;", bootstrap)

    getter = function(account_idl, "int getStructureLotBonus")
    getter = getter.replace("int getStructureLotBonus", "int AccountImplementation::getStructureLotBonus", 1)
    source = MOCKS.replace("COMMAND_METHOD", function(command, "int doQueueCommand("))
    source += "\n" + getter
    source += "\n" + function(account, "bool AccountImplementation::adjustStructureLotBonus(")
    source += "\n" + function(account, "void AccountImplementation::initializeStructureLotBonus(")
    source += "\n" + function(structure, "int StructureManager::getMaximumAccountLots(")
    source += "\n" + CASES

    with tempfile.TemporaryDirectory(prefix=".account-lot-adjustment-", dir=CORE / "bin") as directory:
        directory = Path(directory)
        cpp = directory / "test.cpp"
        executable = directory / "test"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-pedantic", "-pthread",
                                   str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
    print("5 account persistence/legacy schema checks passed")


if __name__ == "__main__":
    main()
