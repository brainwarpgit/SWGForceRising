#!/usr/bin/env python3
"""Test extracted takeover eligibility and queued dispatch under strict C++11.

Uses the real account ledger and account-owner predicate. The transfer boundary
invokes the extracted eligibility predicate, records its arguments, and models a
successful title change; test_account_lot_transfer.py separately executes the
real transfer body. World locks, object loading, and task/reference lifetimes
are mocked. No Core3 or engine3 component is compiled or run.
"""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

CORE = Path(__file__).resolve().parents[3]
MANAGER = CORE / "src/server/zone/managers/structure/StructureManager.cpp"
STRUCTURE = CORE / "src/server/zone/objects/structure/StructureObjectImplementation.cpp"
LEDGER = CORE / "src/server/zone/managers/structure/AccountLotLedger.h"


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


MOCKS = r'''
#include "AccountLotLedger.h"
#include <cstdlib>
#include <functional>
#include <iostream>
#include <string>
#include <vector>
using uint64 = std::uint64_t;
using uint32 = std::uint32_t;
struct String : std::string {
    using std::string::string;
    String(const std::string& value) : std::string(value) {}
    bool isEmpty() const { return empty(); }
};
template<class T> struct Ref {
    T value = nullptr;
    Ref() = default;
    Ref(T value) : value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
};
template<class T> using ManagedReference = Ref<T>;
template<class T, class U> T cast(U value) { return dynamic_cast<T>(value); }
struct Zone {};
struct SceneObject {
    virtual ~SceneObject() {}
    bool noTrade = false, nestedNoTrade = false, vendor = false;
    bool isNoTrade() const { return noTrade; }
    bool containsNoTradeObjectRecursive() const { return nestedNoTrade; }
    bool isVendor() const { return vendor; }
};
struct PlayerObject {
    uint32 account = 1;
    bool online = true, ability = true, privileged = false;
    uint32 getAccountID() const { return account; }
    bool isOnline() const { return online; }
    bool hasAbility(const String&) const { return ability; }
};
struct CreatureObject : SceneObject {
    uint64 id = 12;
    PlayerObject ghost;
    Zone* zone = nullptr;
    SceneObject* rootParent = nullptr;
    bool player = true, missingGhost = false, inRange = true;
    std::vector<String> messages;
    bool isPlayerCreature() const { return player; }
    uint64 getObjectID() const { return id; }
    Ref<PlayerObject*> getPlayerObject() { return missingGhost ? nullptr : &ghost; }
    Zone* getZone() const { return zone; }
    Ref<SceneObject*> getRootParent() { return rootParent; }
    bool isInRange(SceneObject*, float range) const { return range == 16.f && inRange; }
    void sendSystemMessage(const String& message) { messages.push_back(message); }
};
struct SharedStructureObjectTemplate {
    virtual ~SharedStructureObjectTemplate() {}
    String ability;
    const String& getAbilityRequired() const { return ability; }
};
struct CellObject {
    std::vector<SceneObject*> objects;
    int getContainerObjectsSize() const { return objects.size(); }
    Ref<SceneObject*> getContainerObject(int i) { return objects.at(i); }
};
struct StructureObject : SceneObject {
    uint64 ownerObjectID = 11;
    Zone* zone = nullptr;
    SharedStructureObjectTemplate definition;
    bool missingTemplate = false, pending = false;
    bool civic = false, gcw = false, turret = false, minefield = false, scanner = false, camp = false, guild = false;
    Zone* getZone() const { return zone; }
    uint64 getOwnerObjectID() const { return ownerObjectID; }
    bool isPendingDestruction() const { return pending; }
    bool isOwnedByAccount(CreatureObject*) const;
    bool isCivicStructure() const { return civic; }
    bool isGCWBase() const { return gcw; }
    bool isTurret() const { return turret; }
    bool isMinefield() const { return minefield; }
    bool isScanner() const { return scanner; }
    bool isCampStructure() const { return camp; }
    bool isGuildHall() const { return guild; }
    virtual bool isBuildingObject() const { return false; }
    SharedStructureObjectTemplate* getObjectTemplate() { return missingTemplate ? nullptr : &definition; }
};
struct BuildingObject : StructureObject {
    bool residence = false;
    std::vector<CellObject*> cells;
    bool isBuildingObject() const override { return true; }
    bool isResidence() const { return residence; }
    int getTotalCellNumber() const { return cells.size(); }
    Ref<CellObject*> getCell(int i) { return cells.at(i - 1); }
};
struct StructureManager {
    static StructureManager* current;
    AccountLotLedger ledger;
    static StructureManager* instance() { return current; }
    bool isOwnerAccount(uint64 owner, uint32 account) const { return ledger.belongsToAccount(owner, account); }
    bool canTakeOwnership(CreatureObject*, StructureObject*);
    int takeOwnership(CreatureObject*, StructureObject*);
};
StructureManager* StructureManager::current = nullptr;
struct TaskManager {
    std::vector<std::function<void()> > queued;
    void executeTask(std::function<void()> task, const char*) { queued.push_back(task); }
    void run() { auto task = queued.front(); queued.erase(queued.begin()); task(); }
};
struct Core {
    static TaskManager tasks;
    static TaskManager* getTaskManager() { return &tasks; }
};
TaskManager Core::tasks;
struct QueueCommand { static constexpr int SUCCESS = 0; };
bool selectedObjectLocked = false;
struct TransferstructureCommand {
    static int calls;
    static bool validArguments, inheritedLock;
    static int doTransferStructure(CreatureObject* actor, CreatureObject* target, StructureObject* structure, bool force, bool account) {
        ++calls; validArguments = actor == target && force && account; inheritedLock = selectedObjectLocked;
        if (!validArguments || !StructureManager::instance()->canTakeOwnership(target, structure)) return 1;
        structure->ownerObjectID = target->id;
        return QueueCommand::SUCCESS;
    }
};
int TransferstructureCommand::calls = 0;
bool TransferstructureCommand::validArguments = false, TransferstructureCommand::inheritedLock = false;
'''

TESTS = r'''
int checks = 0;
void check(bool value, const char* message) {
    if (!value) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); } ++checks;
}
struct Fixture {
    StructureManager manager;
    CreatureObject player;
    BuildingObject building;
    StructureObject installation;
    SceneObject item;
    CellObject cell;
    Zone zone, otherZone;
    Fixture() {
        StructureManager::current = &manager;
        manager.ledger.registerOwner(11, 1); manager.ledger.registerOwner(12, 1); manager.ledger.registerOwner(21, 2);
        manager.ledger.setStructure(100, 11, 10); manager.ledger.setReady(true);
        player.zone = &zone; building.zone = &zone; installation.zone = &zone;
        player.rootParent = &building; building.cells.push_back(nullptr); building.cells.push_back(&cell);
        cell.objects.push_back(nullptr); cell.objects.push_back(&item);
        Core::tasks.queued.clear(); TransferstructureCommand::calls = 0; selectedObjectLocked = false;
    }
    void mutate(int mode) {
        if (mode == 0) building.residence = true;
        if (mode == 1) building.ownerObjectID = 21;
        if (mode == 2) building.ownerObjectID = player.id;
        if (mode == 3) player.rootParent = nullptr;
        if (mode == 4) { building.definition.ability = "required"; player.ghost.ability = false; }
        if (mode == 5) item.noTrade = true;
        if (mode == 6) item.nestedNoTrade = true;
        if (mode == 7) building.pending = true;
        if (mode == 8) player.zone = &otherZone;
        if (mode == 9) player.ghost.online = false;
        if (mode == 10) player.ghost.account = 0;
        if (mode == 11) building.zone = nullptr;
        if (mode == 12) building.missingTemplate = true;
        if (mode == 13) player.missingGhost = true;
        if (mode == 14) player.player = false;
        if (mode == 15) manager.ledger.setReady(false);
    }
};
int main() {
    {
        Fixture f;
        check(f.manager.canTakeOwnership(&f.player, &f.building), "same-account alt inside ordinary building may take title");
        check(f.manager.canTakeOwnership(&f.player, &f.installation), "same-account alt within 16m of installation may take title");
        f.player.inRange = false;
        check(!f.manager.canTakeOwnership(&f.player, &f.installation), "installation requires range");
        check(f.manager.canTakeOwnership(&f.player, &f.building), "inside building does not require exterior range");
        check(!f.manager.canTakeOwnership(nullptr, &f.building) && !f.manager.canTakeOwnership(&f.player, nullptr), "null actor or structure rejected");
        f.item.noTrade = f.item.nestedNoTrade = f.item.vendor = true;
        check(f.manager.canTakeOwnership(&f.player, &f.building), "vendor exemption matches ordinary transfer contents rule");
    }
    for (int mode = 0; mode < 16; ++mode) {
        Fixture f; f.mutate(mode);
        check(!f.manager.canTakeOwnership(&f.player, &f.building), "current eligibility rejects invalid state");
        check(f.manager.takeOwnership(&f.player, &f.building) != 0 && Core::tasks.queued.empty(), "invalid selection schedules no transfer");
    }
    for (int type = 0; type < 7; ++type) {
        Fixture f;
        if (type == 0) f.building.civic = true;
        if (type == 1) f.building.gcw = true;
        if (type == 2) f.building.turret = true;
        if (type == 3) f.building.minefield = true;
        if (type == 4) f.building.scanner = true;
        if (type == 5) f.building.camp = true;
        if (type == 6) f.building.guild = true;
        check(!f.manager.canTakeOwnership(&f.player, &f.building), "special ownership type is excluded");
    }
    {
        Fixture f; f.player.ghost.account = 2; f.player.ghost.privileged = true;
        check(!f.manager.canTakeOwnership(&f.player, &f.building), "staff cannot use account radial on another account");
    }
    {
        Fixture f; selectedObjectLocked = true;
        check(f.manager.takeOwnership(&f.player, &f.building) == 0, "valid radial accepts takeover request");
        check(Core::tasks.queued.size() == 1 && TransferstructureCommand::calls == 0, "radial defers transfer while selected-object lock is inherited");
        check(f.building.ownerObjectID == 11, "queued request does not mutate title immediately");
        selectedObjectLocked = false; Core::tasks.run();
        check(TransferstructureCommand::calls == 1 && TransferstructureCommand::validArguments && !TransferstructureCommand::inheritedLock,
              "deferred call uses actor as recipient and explicit forced account mode outside radial locks");
        check(f.building.ownerObjectID == f.player.id && f.player.messages.back() == "You are now the named owner of this structure.", "successful task confirms new title owner");
    }
    for (int mode = 0; mode < 12; ++mode) {
        Fixture f;
        f.manager.takeOwnership(&f.player, &f.building);
        f.mutate(mode);
        auto ownerBeforeTask = f.building.ownerObjectID;
        Core::tasks.run();
        check(TransferstructureCommand::calls == 1 && f.building.ownerObjectID == ownerBeforeTask, "state changed after radial cannot mutate title at transfer boundary");
        check(f.player.messages.back().find("Ownership was not changed.") == 0, "queued rejection reports unchanged ownership");
    }
    {
        Fixture f; f.manager.takeOwnership(&f.player, &f.installation); f.player.inRange = false; Core::tasks.run();
        check(f.installation.ownerObjectID == 11, "moving away while installation takeover is queued cancels title change");
    }
    std::cout << "Passed " << checks << " account structure takeover checks\n";
}
'''


def main():
    manager = MANAGER.read_text()
    methods = function(STRUCTURE.read_text(), "bool StructureObjectImplementation::isOwnedByAccount(")
    methods = methods.replace("StructureObjectImplementation::", "StructureObject::")
    methods += "\n" + function(manager, "bool StructureManager::canTakeOwnership(")
    methods += "\n" + function(manager, "int StructureManager::takeOwnership(")
    with tempfile.TemporaryDirectory(prefix="account-structure-takeover-", dir=CORE / "bin") as directory:
        source, executable = Path(directory) / "takeover.cpp", Path(directory) / "takeover"
        source.write_text(MOCKS + "\n" + methods + "\n" + TESTS)
        subprocess.run(shlex.split(os.environ.get("CXX", "g++")) + ["-std=c++11", "-Wall", "-Wextra",
                       "-pedantic-errors", "-pthread", "-I", str(LEDGER.parent), str(source), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
