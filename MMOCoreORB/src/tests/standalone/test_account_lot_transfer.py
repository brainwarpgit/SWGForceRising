#!/usr/bin/env python3
"""Run the extracted transfer command with stdlib mocks and the real lot ledger.

No Core3 or engine3 components are compiled. Mocks model owner-list residence
clearing and track lock scopes, but actual object locks, database writes, city
callbacks, and client cell permissions still require Core3 integration testing.
"""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

CORE = Path(__file__).resolve().parents[3]
COMMAND = CORE / "src/server/zone/objects/creature/commands/TransferstructureCommand.h"
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
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
using uint64 = std::uint64_t;
using String = std::string;
constexpr int SUCCESS = 0, GENERALERROR = 1, TOOFAR = 2;
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
struct StringIdChatParameter {
    StringIdChatParameter(const char*) {}
    void setTO(const char*) {}
    template<class T> void setTT(T) {}
    void setStringId(const char*) {}
};
struct CityRegion {
    bool banned = false, zoning = false, rights = true;
    bool isBanned(uint64) const { return banned; }
    bool isZoningEnabled() const { return zoning; }
    bool hasZoningRights(uint64) const { return rights; }
};
int entityLocks = 0;
std::function<void()> onEntityLock;
struct Locker {
    bool entity = false;
    Locker(Ref<CityRegion*>) {}
    template<class... Args> Locker(Args...) : entity(true) {
        ++entityLocks;
        if (onEntityLock) { auto callback = onEntityLock; onEntityLock = {}; callback(); }
    }
    void release() { if (entity) { --entityLocks; entity = false; } }
    ~Locker() { release(); }
};
struct StructureObject;
struct CreatureObject;
struct PlayerObject {
    unsigned account = 1;
    bool online = true;
    uint64 residence = 0;
    std::set<uint64> owned;
    bool isOnline() const { return online; }
    uint64 getDeclaredResidence() const { return residence; }
    void removeOwnedStructure(StructureObject*);
    void addOwnedStructure(StructureObject*);
};
struct CityManager {
    CreatureObject* removed = nullptr;
    int calls = 0, locksDuringRemoval = -1;
    bool committedBeforeRemoval = false;
    StructureObject* observed = nullptr;
    uint64 expectedOwner = 0;
    void unregisterCitizen(CityRegion*, CreatureObject*);
};
struct ZoneServer { CityManager city; CityManager* getCityManager() { return &city; } };
struct CreatureObject {
    uint64 id;
    PlayerObject ghost;
    ZoneServer* server;
    bool inRange = true, missingGhost = false;
    int messages = 0;
    CreatureObject(uint64 id, unsigned account, ZoneServer* server) : id(id), server(server) { ghost.account = account; }
    uint64 getObjectID() const { return id; }
    Ref<PlayerObject*> getPlayerObject() { return missingGhost ? nullptr : &ghost; }
    bool isInRange(CreatureObject*, float) const { return inRange; }
    template<class T> void sendSystemMessage(const T&) { ++messages; }
    ZoneServer* getZoneServer() { return server; }
    String getFirstName() const { return std::to_string(id); }
};
struct StructureObject {
    virtual ~StructureObject() = default;
    uint64 id = 100, owner = 11;
    int lots = 10, commits = 0;
    CreatureObject* previous = nullptr;
    CityRegion* region = nullptr;
    bool publicStructure = false, rejectCommit = false, pendingDestruction = false;
    uint64 resetPermissions = 0, granted = 0, revoked = 0;
    uint64 getOwnerObjectID() const { return owner; }
    Ref<CreatureObject*> getOwnerCreatureObject() { return previous; }
    uint64 getObjectID() const { return id; }
    int getLotSize() const { return lots; }
    bool isPendingDestruction() const { return pendingDestruction; }
    Ref<CityRegion*> getCityRegion() { return region; }
    void setOwner(uint64, uint64);
    int getSurplusMaintenance() const { return 0; }
    int getSurplusPower() const { return 0; }
    void revokeAllPermissions(uint64 id) { resetPermissions = id; }
    void grantPermission(const char*, uint64 id) { granted = id; }
    void revokePermission(const char*, uint64 id) { revoked = id; }
    bool isBuildingObject() const { return true; }
    bool isPublicStructure() const { return publicStructure; }
};
struct BuildingObject : StructureObject {
    bool residence = true;
    int refreshes = 0;
    void setResidence(bool value) { residence = value; }
    void broadcastCellPermissions() { ++refreshes; }
};
void PlayerObject::removeOwnedStructure(StructureObject* structure) {
    owned.erase(structure->id);
    if (residence == structure->id) residence = 0;
}
void PlayerObject::addOwnedStructure(StructureObject* structure) { owned.insert(structure->id); }
void CityManager::unregisterCitizen(CityRegion*, CreatureObject* player) {
    removed = player; ++calls; locksDuringRemoval = entityLocks;
    committedBeforeRemoval = observed->commits == 1 && observed->owner == expectedOwner;
}
struct StructureManager {
    static StructureManager* current;
    AccountLotLedger ledger;
    int capacity = 10, reserves = 0, releases = 0;
    int takeoverChecks = 0;
    bool takeoverAllowed = true;
    static StructureManager* instance() { return current; }
    bool canTakeOwnership(CreatureObject*, StructureObject*) { ++takeoverChecks; return takeoverAllowed; }
    uint64 reserveAccountLots(PlayerObject* ghost, int lots, uint64 structure) {
        ++reserves; return ledger.reserve(ghost->account, capacity, lots, structure);
    }
    void releaseAccountLots(uint64 token) { ++releases; ledger.release(token); }
    struct LotReservationGuard {
        StructureManager* manager; uint64 token;
        LotReservationGuard(StructureManager* manager, uint64 token) : manager(manager), token(token) {}
        ~LotReservationGuard() { manager->releaseAccountLots(token); }
    };
};
StructureManager* StructureManager::current = nullptr;
void StructureObject::setOwner(uint64 target, uint64 token) {
    if (rejectCommit || !StructureManager::current->ledger.setStructure(id, target, lots, token))
        throw std::runtime_error("owner commit rejected");
    owner = target; ++commits;
}
struct TrxCode { static constexpr int TRANSFERSTRUCT = 1; };
struct TransactionLog {
    template<class... Args> TransactionLog(Args...) {}
    void addState(const char*, int) {}
    void addRelatedObject(uint64, bool) {}
    void setExportRelatedObjects(bool) {}
};
'''

TESTS = r'''
int checks = 0;
void check(bool condition, const char* message) {
    if (!condition) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
    ++checks;
}
struct Fixture {
    StructureManager manager;
    ZoneServer server;
    CreatureObject owner{11, 1, &server}, target{12, 1, &server}, admin{31, 3, &server};
    CityRegion city;
    BuildingObject building;
    Fixture(bool sameAccount = true) {
        StructureManager::current = &manager;
        target.ghost.account = sameAccount ? 1 : 2;
        manager.ledger.registerOwner(owner.id, 1);
        manager.ledger.registerOwner(target.id, target.ghost.account);
        manager.ledger.registerOwner(admin.id, 3);
        manager.ledger.setStructure(building.id, owner.id, building.lots);
        manager.ledger.setReady(true);
        building.previous = &owner; building.region = &city;
        owner.ghost.owned.insert(building.id); owner.ghost.residence = building.id;
        admin.ghost.owned.insert(999); admin.ghost.residence = 999;
        server.city.observed = &building; server.city.expectedOwner = target.id;
        entityLocks = 0; onEntityLock = {};
    }
    int run(bool force = false) { return TransferstructureCommand::doTransferStructure(&admin, &target, &building, force); }
    int remaining(unsigned account) { return manager.ledger.remaining(account, manager.capacity); }
    void unchanged() {
        check(building.owner == owner.id && building.commits == 0, "rejected transfer preserves owner");
        check(owner.ghost.owned.count(building.id) && !target.ghost.owned.count(building.id), "rejected transfer preserves ownership lists");
        check(owner.ghost.residence == building.id && server.city.calls == 0, "rejected transfer preserves residence and citizenship");
        check(building.refreshes == 0 && building.granted == 0, "rejected transfer leaves permissions untouched");
        check(entityLocks == 0, "rejection releases entity locks");
    }
};
int main() {
    {
        Fixture f;
        check(f.remaining(1) == 0, "shared account starts full");
        check(f.run() == SUCCESS && f.remaining(1) == 0, "full shared account transfer succeeds without extra charge");
        check(f.building.owner == f.target.id && f.manager.releases == 1, "transfer commits and guard releases consumed token");
        check(!f.owner.ghost.owned.count(f.building.id) && f.target.ghost.owned.count(f.building.id), "actual previous owner list moves to recipient");
        check(f.admin.ghost.owned == std::set<uint64>{999} && f.admin.ghost.residence == 999, "admin actor ownership and residence stay untouched");
        check(f.owner.ghost.residence == 0 && !f.building.residence, "ownership removal clears previous declared residence");
        check(f.server.city.calls == 1 && f.server.city.removed == &f.owner, "captured residence triggers actual previous citizen removal");
        check(f.server.city.committedBeforeRemoval && f.server.city.locksDuringRemoval == 0, "city removal occurs after commit with player and structure unlocked");
        check(f.building.refreshes == 1, "private permissions are broadcast to all nearby old and new account characters");
        check(f.building.resetPermissions == f.target.id && f.building.granted == f.target.id && f.building.revoked == f.owner.id, "permissions belong to recipient and revoke actual prior owner");
    }
    for (bool force : {false, true}) {
        Fixture f(false);
        f.manager.ledger.setStructure(200, f.target.id, 1);
        check(f.run(force) == GENERALERROR, "normal and forced cross-account transfer reject insufficient capacity");
        f.unchanged();
        check(f.remaining(1) == 0 && f.remaining(2) == 9, "rejection preserves both account balances");
    }
    {
        Fixture f;
        f.target.inRange = false; f.target.ghost.online = false;
        check(TransferstructureCommand::doTransferStructure(nullptr, &f.target, &f.building, true) == SUCCESS,
              "forced guild transfer may use offline recipient without actor");
        check(f.remaining(1) == 0 && f.building.owner == f.target.id, "forced internal transfer preserves account usage");
        check(f.server.city.calls == 1 && f.server.city.removed == &f.owner, "forced transfer cleans actual prior residence");
        check(f.target.messages == 0 && f.admin.messages == 0, "forced transfer skips interactive ownership messages");
    }
    {
        Fixture f(false);
        f.owner.ghost.residence = 999;
        f.building.publicStructure = true;
        check(f.run() == SUCCESS && f.remaining(1) == 10 && f.remaining(2) == 0, "cross-account transfer debits recipient and refunds old account");
        check(f.server.city.calls == 0 && f.owner.ghost.residence == 999, "nonresidence transfer retains citizenship and other residence");
        check(f.building.refreshes == 0, "public building requires no private cell refresh");
    }
    for (int mode = 0; mode < 9; ++mode) {
        Fixture f(false);
        if (mode == 0) f.city.banned = true;
        if (mode == 1) { f.city.zoning = true; f.city.rights = false; }
        if (mode == 2) f.target.inRange = false;
        if (mode == 3) f.target.ghost.online = false;
        if (mode == 4) f.building.rejectCommit = true;
        if (mode == 5) onEntityLock = [&] { f.building.owner = 999; };
        if (mode == 6) onEntityLock = [&] { f.building.lots = 12; };
        if (mode == 7) f.building.pendingDestruction = true;
        if (mode == 8) onEntityLock = [&] { f.building.pendingDestruction = true; };
        int result = GENERALERROR;
        bool threw = false;
        try { result = f.run(); } catch (const std::runtime_error&) { threw = true; }
        check(mode == 4 ? threw : result != SUCCESS, "city range ownership and commit failures reject transfer");
        if (mode == 5) f.building.owner = f.owner.id;
        f.unchanged();
        check(f.remaining(1) == 0 && f.remaining(2) == 10, "failed transfer releases any recipient reservation");
    }
    for (bool force : {false, true}) {
        Fixture f;
        check(TransferstructureCommand::doTransferStructure(&f.admin, &f.owner, &f.building, force) == GENERALERROR, "normal and forced transfer to existing owner rejected");
        check(f.manager.reserves == 0, "same-owner rejection happens before reserving lots");
        f.unchanged();
    }
    {
        Fixture f;
        f.owner.ghost.online = false;
        f.owner.ghost.residence = 0;
        f.building.residence = false;
        check(TransferstructureCommand::doTransferStructure(&f.target, &f.target, &f.building, true, true) == SUCCESS,
              "account takeover accepts offline title owner on full shared account");
        check(f.remaining(1) == 0 && f.building.owner == f.target.id, "account takeover preserves full shared lot usage");
        check(!f.owner.ghost.owned.count(f.building.id) && f.target.ghost.owned.count(f.building.id),
              "account takeover moves offline title owner record to acting character");
        check(f.server.city.calls == 0 && f.building.refreshes == 1, "nonresidence takeover refreshes access without citizenship changes");
        check(f.manager.takeoverChecks >= 2, "account takeover validates before reserving and at owner commit");
    }
    for (int mode = 0; mode < 4; ++mode) {
        Fixture f;
        f.owner.ghost.residence = 0;
        f.building.residence = false;
        if (mode == 0) f.manager.takeoverAllowed = false;
        if (mode == 1) onEntityLock = [&] { f.manager.takeoverAllowed = false; };
        if (mode == 2) onEntityLock = [&] { f.owner.ghost.residence = f.building.id; };
        if (mode == 3) f.owner.ghost.residence = f.building.id;
        check(TransferstructureCommand::doTransferStructure(&f.target, &f.target, &f.building, true, true) != SUCCESS,
              "takeover rejects lost eligibility or declared residence before commit");
        check(f.building.owner == f.owner.id && f.building.commits == 0, "rejected takeover does not change title owner");
        check(f.owner.ghost.owned.count(f.building.id) && !f.target.ghost.owned.count(f.building.id), "rejected takeover retains offline ownership bookkeeping");
        check(f.remaining(1) == 0 && f.server.city.calls == 0 && f.building.refreshes == 0, "rejected takeover leaves lots citizenship and permissions unchanged");
        check(entityLocks == 0, "rejected takeover releases entity locks");
    }
    for (bool takeover : {false, true}) {
        Fixture f;
        f.owner.ghost.residence = 0;
        f.building.residence = false;
        f.building.previous = &f.admin;
        check(TransferstructureCommand::doTransferStructure(&f.target, &f.target, &f.building, true, takeover) != SUCCESS,
              "resolved prior owner must match captured title owner even for forced transfers");
        check(f.manager.reserves == 0 && f.building.owner == f.owner.id, "owner lookup mismatch is rejected before reservation and commit");
        check(f.owner.ghost.owned.count(f.building.id) && f.admin.ghost.owned == std::set<uint64>{999}, "owner mismatch cannot remove structures from either character");
        check(f.remaining(1) == 0 && f.building.refreshes == 0, "owner lookup mismatch leaves lots and access unchanged");
    }
    std::cout << "Passed " << checks << " account-lot transfer checks\n";
}
'''


def main():
    method = function(COMMAND.read_text(), "static int doTransferStructure(")
    harness = MOCKS + "\nstruct TransferstructureCommand {\n" + method + "\n};\n" + TESTS
    with tempfile.TemporaryDirectory(prefix="account-lot-transfer-", dir=CORE / "bin") as directory:
        source, executable = Path(directory) / "transfer.cpp", Path(directory) / "transfer"
        source.write_text(harness)
        subprocess.run(shlex.split(os.environ.get("CXX", "g++")) + [
            "-std=c++11", "-Wall", "-Wextra", "-pedantic-errors", "-pthread", "-I", str(LEDGER.parent),
            str(source), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
