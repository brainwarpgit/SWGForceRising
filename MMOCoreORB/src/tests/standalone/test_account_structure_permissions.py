#!/usr/bin/env python3
"""Test extracted structure permissions with the real account-lot ledger.

Only standard-library mocks and the standalone ledger header are compiled.
No Core3 component, generated IDL code, or engine3 header is built; persistent
object loading, game-object locks, and client behavior need runtime validation.
"""

import os
from pathlib import Path
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
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
#include "server/zone/managers/structure/AccountLotLedger.h"
using uint32 = uint32_t;
using uint64 = uint64_t;
using String = std::string;
using Exception = std::runtime_error;
using UnicodeString = std::string;
template<class T> using Vector = std::vector<T>;
template<class T> struct Ref {
    T value;
    Ref(T value = nullptr): value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
};
template<class T> using ManagedReference = Ref<T>;
template<class T, class U> T cast(U* value) { return static_cast<T>(value); }
struct SceneObject {
    uint64 id;
    bool locked = false;
    explicit SceneObject(uint64 id): id(id) {}
    virtual ~SceneObject() {}
    virtual bool isPlayerCreature() const { return false; }
    virtual bool isBuildingObject() const { return false; }
    virtual bool isPobShip() const { return false; }
    uint64 getObjectID() const { return id; }
};
struct GuildObject: SceneObject { explicit GuildObject(uint64 id): SceneObject(id) {} };
struct PlayerObject {
    uint32 accountID;
    bool privileged = false, god = false;
    explicit PlayerObject(uint32 accountID): accountID(accountID) {}
    uint32 getAccountID() const { return accountID; }
    bool isPrivileged() const { return privileged; }
    bool hasGodMode() const { return god; }
};
struct CreatureObject: SceneObject {
    PlayerObject* ghost;
    GuildObject* guild = nullptr;
    bool player = true;
    std::vector<String> messages;
    CreatureObject(uint64 id, PlayerObject* ghost): SceneObject(id), ghost(ghost) {}
    bool isPlayerCreature() const override { return player; }
    PlayerObject* getPlayerObject() const { return ghost; }
    Ref<GuildObject*> getGuildObject() const { return guild; }
    void sendSystemMessage(const String& message) { messages.push_back(message); }
};
struct ZoneServer {
    std::map<uint64, SceneObject*> objects;
    int lookups = 0;
    SceneObject* getObject(uint64 id) {
        ++lookups;
        auto found = objects.find(id);
        return found == objects.end() ? nullptr : found->second;
    }
};
struct PermissionList {
    uint64 owner = 0;
    std::map<String, std::set<uint64>> lists;
    void setOwner(uint64 id) { owner = id; }
    bool isOnPermissionList(const String& name, uint64 id) const {
        if (name != "BAN" && id == owner) return true;
        auto found = lists.find(name);
        return found != lists.end() && found->second.count(id) != 0;
    }
};
struct StructureObjectImplementation;
struct StructureManager {
    static StructureManager* current;
    static StructureManager* instance() { return current; }
    AccountLotLedger accountLots;
    OWNER_ACCOUNT_METHOD
    bool updateStructureLotOwner(StructureObjectImplementation* structure, uint64 owner, uint64 reservation);
};
StructureManager* StructureManager::current = nullptr;
struct StructureObjectImplementation {
    struct Self {
        StructureObjectImplementation* value;
        StructureObjectImplementation* getReferenceUnsafeStaticCast() { return value; }
    } _this;
    uint64 ownerObjectID = 10;
    bool pendingDestruction = false;
    ZoneServer* server;
    PermissionList structurePermissionList;
    explicit StructureObjectImplementation(ZoneServer* server): _this{this}, server(server) {
        structurePermissionList.setOwner(ownerObjectID);
    }
    ZoneServer* getZoneServer() const { return server; }
    void setOwner(uint64 id, uint64 reservation = 0);
    bool isOwnedByAccount(CreatureObject* player) const;
    bool isOwnerOf(SceneObject* obj) const;
    bool isOwnerOf(uint64 id) const;
    bool isOnAdminList(CreatureObject* player) const;
    bool isOnEntryList(CreatureObject* player) const;
    bool isOnBanList(CreatureObject* player) const;
    bool isOnHopperList(CreatureObject* player) const;
    bool isOnPermissionList(const String& listName, CreatureObject* player) const;
    bool isOnPermissionList(const String& listName, const uint64 objectID) const;
    bool isOnAdminList(const uint64 objectID) const;
    bool isOnBanList(const uint64 objectID) const;
};
bool StructureManager::updateStructureLotOwner(StructureObjectImplementation*, uint64 owner, uint64 reservation) {
    return accountLots.setStructure(100, owner, 5, reservation);
}
struct Fixture {
    StructureManager manager;
    ZoneServer server;
    PlayerObject titleGhost{7}, altGhost{7}, otherGhost{8}, otherAltGhost{8}, staffGhost{9};
    CreatureObject title{10, &titleGhost}, alt{11, &altGhost}, other{20, &otherGhost};
    CreatureObject otherAlt{21, &otherAltGhost}, staff{30, &staffGhost}, npc{40, &altGhost};
    GuildObject guild{50};
    StructureObjectImplementation structure{&server};
    Fixture() {
        StructureManager::current = &manager;
        manager.accountLots.registerOwner(title.id, 7);
        manager.accountLots.registerOwner(alt.id, 7);
        manager.accountLots.registerOwner(other.id, 8);
        manager.accountLots.registerOwner(otherAlt.id, 8);
        manager.accountLots.registerOwner(staff.id, 9);
        manager.accountLots.setStructure(100, title.id, 5);
        manager.accountLots.setReady(true);
        npc.player = false;
        server.objects = {{10, &title}, {11, &alt}, {20, &other}, {21, &otherAlt}, {30, &staff}, {40, &npc}, {50, &guild}};
    }
};
struct BuildingObject: SceneObject, StructureObjectImplementation {
    int deletions = 0;
    explicit BuildingObject(ZoneServer* server): SceneObject(100), StructureObjectImplementation(server) {}
    bool isBuildingObject() const override { return true; }
    bool isOnAdminList(CreatureObject* player) const {
        assert(locked); // The callback must recheck access while holding its structure lock.
        return StructureObjectImplementation::isOnAdminList(player);
    }
    void destroyAllPlayerItems() { assert(locked); ++deletions; }
};
struct PobShipObject: SceneObject {
    int deletions = 0;
    PobShipObject(): SceneObject(200) {}
    bool isPobShip() const override { return true; }
    void destroyAllPlayerItems() { assert(locked); ++deletions; }
};
struct SuiBox {
    SceneObject* usingObject;
    bool messageBox = true;
    explicit SuiBox(SceneObject* usingObject): usingObject(usingObject) {}
    bool isMessageBox() const { return messageBox; }
    Ref<SceneObject*> getUsingObject() const { return usingObject; }
};
struct Locker {
    SceneObject* object;
    Locker(SceneObject* object, CreatureObject*): object(object) {
        assert(!object->locked);
        object->locked = true;
    }
    ~Locker() { object->locked = false; }
};
int transactions = 0;
struct TrxCode { enum { PLAYERMISCACTION }; };
struct TransactionLog {
    TransactionLog(int, CreatureObject*, SceneObject* object) { assert(object->locked); ++transactions; }
    bool isVerbose() const { return false; }
    void addRelatedObject(SceneObject*, bool) {}
    void setExportRelatedObjects(bool) {}
    void exportRelated() {}
};
struct DeleteAllItemsConfirmSuiCallback {
    DELETE_CALLBACK_METHOD
};
'''


CASES = r'''
int main() {
    int checks = 0;
    auto check = [&](bool passed, const char* description) {
        if (!passed) { std::cerr << "Failed: " << description << '\n'; std::abort(); }
        ++checks;
    };
    {
        Fixture f;
        for (auto* owner : {&f.title, &f.alt}) {
            check(f.structure.isOwnedByAccount(owner), "title and account sibling have ownership");
            check(f.structure.isOwnerOf(owner), "object owner overload grants account rights");
            check(f.structure.isOwnerOf(owner->id), "numeric owner overload grants account rights");
            check(f.structure.isOnAdminList(owner), "account owner has admin rights");
            check(f.structure.isOnEntryList(owner), "account owner has entry rights");
            check(f.structure.isOnHopperList(owner), "account owner has hopper rights");
            check(!f.structure.isOnBanList(owner), "account owner is not banned");
            for (const auto* list : {"ADMIN", "ENTRY", "HOPPER", "VENDOR"}) {
                check(f.structure.isOnPermissionList(list, owner), "named object permission grants account rights");
                check(f.structure.isOnPermissionList(list, owner->id), "named numeric permission grants account rights");
            }
            check(f.structure.isOnAdminList(owner->id), "numeric admin wrapper grants account rights");
            check(!f.structure.isOnBanList(owner->id), "numeric ban wrapper excludes account owner");
        }
        check(f.structure.ownerObjectID == f.title.id, "permission checks retain actual title owner");
        check(f.structure.structurePermissionList.lists.empty(), "account rights add no explicit permission records");
        check(!f.structure.isOwnedByAccount(&f.other), "unrelated account is not owner");
        check(!f.structure.isOnAdminList(&f.other), "unrelated account has no implicit admin");
        check(!f.structure.isOnEntryList(&f.other), "unrelated account has no implicit entry");
        check(!f.structure.isOnHopperList(&f.other), "unrelated account has no implicit hopper");
    }
    {
        Fixture f;
        f.server.objects.erase(f.title.id);
        f.title.ghost = nullptr;
        f.server.lookups = 0;
        check(f.structure.isOwnedByAccount(&f.alt), "offline unloaded title owner still grants sibling rights");
        check(f.structure.isOnAdminList(&f.alt), "offline title owner still grants admin");
        check(f.server.lookups == 0, "account predicate does not load the title owner");
        check(f.structure.isOnAdminList(f.alt.id), "numeric sibling permission resolves only candidate");
        CreatureObject newCharacter(12, &f.altGhost);
        check(f.structure.isOwnedByAccount(&newCharacter), "new sibling requires no explicit ledger registration");
    }
    {
        Fixture f;
        check(!f.structure.isOwnedByAccount(nullptr), "null candidate has no account ownership");
        check(!f.structure.isOwnerOf(static_cast<SceneObject*>(nullptr)), "null object has no ownership");
        for (auto* nonplayer : {static_cast<SceneObject*>(&f.npc), static_cast<SceneObject*>(&f.guild)}) {
            check(!f.structure.isOwnerOf(nonplayer), "nonplayer object cannot obtain owner rights");
            check(!f.structure.isOwnerOf(nonplayer->id), "nonplayer numeric ID cannot obtain owner rights");
        }
        check(!f.structure.isOwnedByAccount(&f.npc), "NPC cannot borrow its ghost account");
        f.npc.id = f.title.id;
        check(!f.structure.isOwnedByAccount(&f.npc), "matching title ID does not make NPC a player owner");
        f.alt.ghost = nullptr;
        check(!f.structure.isOwnedByAccount(&f.alt), "sibling without ghost denied");
        f.alt.ghost = &f.altGhost;
        f.altGhost.accountID = 0;
        check(!f.structure.isOwnedByAccount(&f.alt), "zero account denied");
        f.altGhost.accountID = 999;
        check(!f.structure.isOwnedByAccount(&f.alt), "unknown account denied");
        f.altGhost.accountID = 7;
        f.structure.ownerObjectID = 0;
        check(!f.structure.isOwnedByAccount(&f.alt), "unowned structure grants no account rights");
        f.structure.ownerObjectID = 9999;
        check(!f.structure.isOwnedByAccount(&f.alt), "unregistered title owner fails closed");
        f.structure.ownerObjectID = f.title.id;
        f.manager.accountLots.setReady(false);
        check(!f.structure.isOwnedByAccount(&f.alt), "unready ledger grants no new account rights");
        check(f.structure.isOwnedByAccount(&f.title), "exact title owner retains access while ledger unready");
        f.manager.accountLots.setReady(true);
        check(f.structure.isOwnedByAccount(&f.alt), "account rights resume when ledger ready");
        f.structure.server = nullptr;
        check(!f.structure.isOwnerOf(f.alt.id), "numeric ownership fails closed without server");
        check(!f.structure.isOnAdminList(f.alt.id), "numeric account admin fails closed without server");
    }
    {
        Fixture f;
        f.staffGhost.privileged = true;
        check(!f.structure.isOwnedByAccount(&f.staff), "account-only predicate does not grant staff ownership");
        check(f.structure.isOwnerOf(&f.staff) && f.structure.isOwnerOf(f.staff.id), "existing staff owner override preserved");
        check(f.structure.isOnAdminList(&f.staff), "existing staff admin override preserved");
        check(f.structure.isOnHopperList(&f.staff), "existing staff hopper override preserved");
        check(!f.structure.isOnEntryList(&f.staff), "entry still requires god mode or listed permission");
        check(f.structure.isOnPermissionList("VENDOR", &f.staff), "general staff list override preserved");
        check(!f.structure.isOnAdminList(f.staff.id), "numeric list does not acquire new staff override");
        f.structure.structurePermissionList.lists["BAN"].insert(f.staff.id);
        check(f.structure.isOnBanList(&f.staff), "non-god staff direct ban behavior preserved");
        check(!f.structure.isOnPermissionList("BAN", &f.staff), "general staff ban override preserved");
        f.staffGhost.god = true;
        check(f.structure.isOnEntryList(&f.staff), "god mode entry override preserved");
        check(!f.structure.isOnBanList(&f.staff), "god mode ban override preserved");
    }
    for (bool guildGrant : {false, true}) {
        Fixture f;
        if (guildGrant) f.other.guild = &f.guild;
        uint64 grantedID = guildGrant ? f.guild.id : f.other.id;
        f.structure.structurePermissionList.lists["ADMIN"].insert(grantedID);
        check(f.structure.isOnAdminList(&f.other), "explicit or guild admin grant preserved");
        check(f.structure.isOnEntryList(&f.other), "admin grant implies entry");
        check(f.structure.isOnHopperList(&f.other), "admin grant implies hopper");
        check(f.structure.isOnAdminList(grantedID), "numeric explicit player/guild grant preserved");
        check(!f.structure.isOwnedByAccount(&f.other), "permission grants do not make account owner");
        check(!f.structure.isOwnerOf(grantedID), "numeric explicit player/guild grant does not make owner");
        f.structure.structurePermissionList.lists.clear();
        f.structure.structurePermissionList.lists["ENTRY"].insert(grantedID);
        check(f.structure.isOnEntryList(&f.other) && !f.structure.isOnAdminList(&f.other),
              "entry-only explicit/guild grant remains limited");
        f.structure.structurePermissionList.lists.clear();
        f.structure.structurePermissionList.lists["HOPPER"].insert(grantedID);
        check(f.structure.isOnHopperList(&f.other) && !f.structure.isOnAdminList(&f.other),
              "hopper-only explicit/guild grant remains limited");
        f.structure.structurePermissionList.lists.clear();
        f.structure.structurePermissionList.lists["BAN"].insert(grantedID);
        check(f.structure.isOnBanList(&f.other), "explicit/guild bans remain effective for unrelated account");
        check(f.structure.isOnBanList(grantedID), "numeric explicit player/guild ban preserved");
    }
    {
        Fixture f;
        f.alt.guild = &f.guild;
        f.structure.structurePermissionList.lists["BAN"].insert(f.alt.id);
        f.structure.structurePermissionList.lists["BAN"].insert(f.guild.id);
        check(!f.structure.isOnBanList(&f.alt), "account owner bypasses old explicit and guild bans");
        check(!f.structure.isOnBanList(f.alt.id), "numeric account owner bypasses explicit ban");
        check(!f.structure.isOnPermissionList("BAN", &f.alt), "generic account owner ban check consistent");
        check(f.structure.isOnAdminList(&f.alt) && f.structure.isOnEntryList(&f.alt), "bans do not defeat owner rights");
        check(f.structure.isOnBanList(f.guild.id), "account ownership does not remove guild ban for outsiders");
    }
    {
        Fixture f;
        f.structure.setOwner(f.other.id);
        check(f.structure.ownerObjectID == f.other.id && f.structure.structurePermissionList.owner == f.other.id,
              "transfer updates title and permission-list owner");
        check(!f.structure.isOwnedByAccount(&f.title) && !f.structure.isOwnedByAccount(&f.alt),
              "old account immediately loses implicit ownership");
        check(!f.structure.isOnAdminList(&f.alt) && !f.structure.isOnAdminList(f.alt.id),
              "old account immediately loses implicit admin across overloads");
        check(f.structure.isOwnedByAccount(&f.other) && f.structure.isOwnedByAccount(&f.otherAlt),
              "new title owner and sibling immediately gain ownership");
        check(f.structure.isOnAdminList(&f.otherAlt) && f.structure.isOnAdminList(f.otherAlt.id),
              "new account immediately gains admin across overloads");
        check(f.manager.accountLots.remaining(7, 100) == 100 && f.manager.accountLots.remaining(8, 100) == 95,
              "same ledger keeps lot charges with new owner account");
        f.structure.structurePermissionList.lists["ADMIN"].insert(f.alt.id);
        check(f.structure.isOnAdminList(&f.alt) && !f.structure.isOwnedByAccount(&f.alt),
              "explicit former-account grant remains distinct from implicit ownership");
    }
    {
        Fixture f;
        f.structure.pendingDestruction = true;
        bool rejected = false;
        try { f.structure.setOwner(f.other.id); } catch (const Exception&) { rejected = true; }
        check(rejected, "pending destruction rejects an ownership transfer");
        check(f.structure.ownerObjectID == f.title.id && f.structure.isOwnedByAccount(&f.alt),
              "rejected transfer preserves title and existing account rights");
        check(!f.structure.isOwnedByAccount(&f.otherAlt), "rejected transfer grants no new account rights");
    }
    {
        AccountLotLedger ledger;
        check(!ledger.registerOwner(0, 7), "zero owner cannot register");
        check(!ledger.registerOwner(10, 0), "zero account cannot register");
        check(ledger.registerOwner(10, 7), "valid owner mapping registers");
        check(!ledger.belongsToAccount(10, 7), "owner mapping stays unavailable before readiness");
        ledger.setReady(true);
        check(ledger.belongsToAccount(10, 7), "ready owner mapping matches");
        check(!ledger.belongsToAccount(10, 8), "owner mapping rejects another account");
        check(!ledger.belongsToAccount(10, 0), "owner mapping rejects zero account");
        check(!ledger.belongsToAccount(999, 7), "owner mapping rejects unknown owner");
        check(!ledger.registerOwner(10, 8), "owner mapping cannot silently change account");
        check(ledger.belongsToAccount(10, 7), "failed registration preserves existing owner account");
    }
    {
        Fixture f;
        BuildingObject building(&f.server);
        SuiBox dialog(&building);
        DeleteAllItemsConfirmSuiCallback callback;
        transactions = 0;
        callback.run(&f.alt, &dialog, 0, nullptr);
        check(building.deletions == 1 && transactions == 1, "current account admin can confirm delete-all-items");
        check(f.alt.messages.size() == 1 && f.alt.messages[0] == "@player_structure:items_deleted",
              "successful delete-all-items confirms completion");
        check(!building.locked, "callback releases building lock after deletion");
    }
    {
        Fixture f;
        BuildingObject building(&f.server);
        SuiBox staleDialog(&building);
        DeleteAllItemsConfirmSuiCallback callback;
        building.setOwner(f.other.id);
        transactions = 0;
        callback.run(&f.alt, &staleDialog, 0, nullptr);
        check(building.deletions == 0, "stale former-account dialog cannot delete new owner's contents");
        check(transactions == 0 && f.alt.messages.empty(), "rejected stale dialog has no transaction or success message");
        check(!building.locked, "rejected stale dialog releases building lock");
        callback.run(&f.otherAlt, &staleDialog, 0, nullptr);
        check(building.deletions == 1, "new owner's account still has delete-all-items rights");
    }
    {
        Fixture f;
        BuildingObject building(&f.server);
        building.structurePermissionList.lists["ADMIN"].insert(f.other.id);
        SuiBox staleDialog(&building);
        DeleteAllItemsConfirmSuiCallback callback;
        building.structurePermissionList.lists["ADMIN"].erase(f.other.id);
        transactions = 0;
        callback.run(&f.other, &staleDialog, 0, nullptr);
        check(building.deletions == 0 && transactions == 0, "revoked explicit admin cannot use an old dialog");
        building.structurePermissionList.lists["ADMIN"].insert(f.other.id);
        callback.run(&f.other, &staleDialog, 0, nullptr);
        check(building.deletions == 1, "currently granted explicit admin can still delete contents");
    }
    {
        Fixture f;
        BuildingObject building(&f.server);
        SuiBox dialog(&building);
        DeleteAllItemsConfirmSuiCallback callback;
        building.setOwner(f.alt.id);
        callback.run(&f.title, &dialog, 0, nullptr);
        check(building.deletions == 1, "same-account title transfer keeps dialog authorized");
    }
    {
        Fixture f;
        BuildingObject building(&f.server);
        SuiBox dialog(&building);
        DeleteAllItemsConfirmSuiCallback callback;
        transactions = 0;
        callback.run(&f.alt, &dialog, 1, nullptr);
        check(building.deletions == 0 && transactions == 0, "cancel preserves contents");
        dialog.messageBox = false;
        callback.run(&f.alt, &dialog, 0, nullptr);
        check(building.deletions == 0 && transactions == 0, "non-message dialog cannot delete contents");
        dialog.messageBox = true;
        dialog.usingObject = nullptr;
        callback.run(&f.alt, &dialog, 0, nullptr);
        check(transactions == 0, "missing dialog object is rejected");
        dialog.usingObject = &f.guild;
        callback.run(&f.alt, &dialog, 0, nullptr);
        check(transactions == 0, "non-building non-ship dialog object is rejected");
        PobShipObject ship;
        dialog.usingObject = &ship;
        callback.run(&f.other, &dialog, 0, nullptr);
        check(ship.deletions == 1 && transactions == 1, "existing POB callback branch remains unchanged");
    }
    std::cout << checks << " account structure permission checks passed\n";
}
'''


def main():
    structure = (CORE / "src/server/zone/objects/structure/StructureObjectImplementation.cpp").read_text()
    idl = (CORE / "src/server/zone/objects/structure/StructureObject.idl").read_text()
    manager = (CORE / "src/server/zone/managers/structure/StructureManager.h").read_text()
    callback = (CORE / "src/server/zone/objects/player/sui/callbacks/DeleteAllItemsConfirmSuiCallback.h").read_text()
    source = MOCKS.replace("OWNER_ACCOUNT_METHOD", function(manager, "bool isOwnerAccount("))
    source = source.replace("DELETE_CALLBACK_METHOD", function(callback, "void run("))
    signatures = [
        "void StructureObjectImplementation::setOwner(",
        "bool StructureObjectImplementation::isOwnedByAccount(",
        "bool StructureObjectImplementation::isOwnerOf(SceneObject*",
        "bool StructureObjectImplementation::isOwnerOf(uint64",
        "bool StructureObjectImplementation::isOnAdminList(CreatureObject*",
        "bool StructureObjectImplementation::isOnEntryList(CreatureObject*",
        "bool StructureObjectImplementation::isOnBanList(CreatureObject*",
        "bool StructureObjectImplementation::isOnHopperList(CreatureObject*",
        "bool StructureObjectImplementation::isOnPermissionList(const String& listName, CreatureObject*",
        "bool StructureObjectImplementation::isOnPermissionList(const String& listName, const uint64",
    ]
    for signature in signatures:
        source += "\n" + function(structure, signature)
    for name in ["isOnAdminList", "isOnBanList"]:
        method = function(idl, "public boolean " + name + "(final unsigned long")
        body = method[method.index("{"):]
        source += "\nbool StructureObjectImplementation::" + name + "(const uint64 objectID) const " + body
    source += "\n" + CASES

    with tempfile.TemporaryDirectory(prefix=".account-structure-permissions-", dir=CORE / "bin") as directory:
        directory = Path(directory)
        cpp, executable = directory / "test.cpp", directory / "test"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++11", "-Wall", "-Wextra", "-pedantic-errors", "-pthread",
                                   "-I", str(CORE / "src"), str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
