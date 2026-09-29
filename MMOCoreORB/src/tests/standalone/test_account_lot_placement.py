#!/usr/bin/env python3
"""Exercise the production placement lifecycle against an isolated mock world.

The six session methods and completion task are extracted unchanged (apart
from the generated implementation class name). The real stdlib AccountLotLedger
backs the manager boundary. This compiles no Core3/engine3 components. Mocks
replace engine references, locks, world persistence, task scheduling, and mail;
real logout, database recovery, object locking, and placement still need testing
in Core3. Temporary harness files are created under bin and removed afterward.
"""

import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]
SESSION = CORE / "src/server/zone/objects/player/sessions/PlaceStructureSessionImplementation.cpp"
SESSION_IDL = SESSION.with_name("PlaceStructureSession.idl")
TASK = CORE / "src/server/zone/managers/structure/tasks/StructureConstructionCompleteTask.h"
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
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
using uint64 = std::uint64_t;

struct String : std::string {
    using std::string::string;
    String(const std::string& value) : std::string(value) {}
    std::size_t hashCode() const { return std::hash<std::string>{}(*this); }
    bool isEmpty() const { return empty(); }
    bool contains(const char* value) const { return find(value) != npos; }
};
using UnicodeString = String;
#define STRING_HASHCODE(value) String(value).hashCode()
template<class T> struct Ref {
    T value = nullptr;
    Ref() = default;
    Ref(T value) : value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
    template<class U> Ref<U> castTo() const { return dynamic_cast<U>(value); }
};
template<class T> using ManagedReference = Ref<T>;
template<class T> using ManagedWeakReference = Ref<T>;
template<class T> using Reference = Ref<T>;
template<class T, class U> T cast(U value) { return dynamic_cast<T>(value); }
struct Locker {
    template<class... Args> Locker(Args...) {}
    void release() {}
};
struct StringIdChatParameter {
    String text;
    int di = -1;
    StringIdChatParameter(const char* text) : text(text) {}
    void setDI(int value) { di = value; }
    void setTO(const String&) {}
};
struct Zone;
struct CreatureObject;
struct StructureObject;
struct PlaceStructureSession;
struct SessionFacade { virtual ~SessionFacade() = default; };
struct FacadeImplementation : SessionFacade {
    int transientInitializations = 0;
    void initializeTransientMembers() { ++transientInitializations; }
};
struct SessionFacadeType { static constexpr int PLACESTRUCTURE = 1; };

struct SceneObject {
    virtual ~SceneObject() = default;
    uint64 id = 100;
    SceneObject* parent = nullptr;
    Zone* worldZone = nullptr;
    int destroyed = 0, transfers = 0;
    bool transferFails = false, overflowAllowed = false;
    uint64 getObjectID() const { return id; }
    SceneObject* getParent() const { return parent; }
    Zone* getZone() const { return worldZone; }
    void initializePosition(float, float, float) {}
    void rotate(int) {}
    void setCustomObjectName(const String&, bool) {}
    void destroyObjectFromWorld(bool) { ++destroyed; parent = nullptr; worldZone = nullptr; }
    bool transferObject(SceneObject* object, int, bool, bool overflow = false) {
        ++transfers;
        overflowAllowed = overflow;
        if (transferFails) return false;
        object->parent = this;
        object->worldZone = nullptr;
        return true;
    }
};
std::vector<std::unique_ptr<SceneObject>> objects;
template<class T> T* makeObject() {
    auto object = std::make_unique<T>();
    auto pointer = object.get();
    pointer->id = 1000 + objects.size();
    objects.push_back(std::move(object));
    return pointer;
}
struct CircularAreaShape {
    void setRadius(int) {}
    void setAreaCenter(float, float) {}
};
struct ActiveArea : SceneObject {
    static constexpr int NOBUILDZONEAREA = 1;
    void setAreaShape(CircularAreaShape* shape) { delete shape; }
    void addAreaFlag(int) {}
};
struct WaypointObject : SceneObject {
    void setActive(bool) {}
    void setPosition(float, float, float) {}
    void setPlanetCRC(int) {}
};
struct ChatManager {
    int messages = 0;
    void sendMail(const char*, const String&, const StringIdChatParameter&, const String&, WaypointObject*) { ++messages; }
};
struct ZoneServer {
    bool failArea = false;
    int areaCreates = 0;
    ChatManager chat;
    Ref<SceneObject*> createObject(std::size_t hash, int) {
        if (hash == STRING_HASHCODE("object/active_area.iff")) {
            ++areaCreates;
            return failArea ? nullptr : makeObject<ActiveArea>();
        }
        return makeObject<WaypointObject>();
    }
    ChatManager* getChatManager() { return &chat; }
};
struct GCWManager { int getBasePlacementDelay() const { return 20; } };
struct Zone {
    ZoneServer server;
    GCWManager gcw;
    bool failAreaTransfer = false, failMarkerTransfer = false;
    int transfers = 0;
    ZoneServer* getZoneServer() { return &server; }
    GCWManager* getGCWManager() { return &gcw; }
    int getZoneCRC() const { return 77; }
    bool transferObject(SceneObject* object, int, bool) {
        ++transfers;
        if (dynamic_cast<ActiveArea*>(object) ? failAreaTransfer : failMarkerTransfer) return false;
        object->worldZone = this;
        object->parent = nullptr;
        return true;
    }
};
struct StructureFootprint {
    int getRowSize() const { return 2; }
    int getColSize() const { return 1; }
};
struct SharedStructureObjectTemplate {
    virtual ~SharedStructureObjectTemplate() = default;
    int lots = 6;
    String marker = "marker.iff";
    StructureFootprint footprint;
    int getLotSize() const { return lots; }
    String getConstructionMarkerTemplate() const { return marker; }
    const StructureFootprint* getStructureFootprint() const { return &footprint; }
};
struct TemplateManager {
    static TemplateManager* current;
    SharedStructureObjectTemplate definition;
    bool missing = false;
    static TemplateManager* instance() { return current; }
    SharedStructureObjectTemplate* getTemplate(std::size_t) { return missing ? nullptr : &definition; }
};
TemplateManager* TemplateManager::current = nullptr;
struct ObjectManager {
    static ObjectManager* current;
    bool throwOnCreate = false;
    int creates = 0;
    static ObjectManager* instance() { return current; }
    SceneObject* createObject(std::size_t, int, const char*) {
        ++creates;
        if (throwOnCreate) throw std::runtime_error("marker creation failure");
        return makeObject<SceneObject>();
    }
};
ObjectManager* ObjectManager::current = nullptr;
struct PlayerObject {
    uint64 owner = 11;
    unsigned account = 1;
    int waypoints = 0;
    int getLotsRemaining();
    void addWaypoint(WaypointObject*, bool, bool) { ++waypoints; }
};
struct CreatureObject {
    PlayerObject ghost;
    Zone* worldZone = nullptr;
    SceneObject inventory;
    SessionFacade* active = nullptr;
    bool missingGhost = false, missingInventory = false;
    int drops = 0, messages = 0, lastDI = -1;
    PlayerObject* getPlayerObject() { return missingGhost ? nullptr : &ghost; }
    Zone* getZone() const { return worldZone; }
    Ref<SceneObject*> getSlottedObject(const char*) { return missingInventory ? nullptr : &inventory; }
    Ref<SessionFacade*> getActiveSession(int) { return active; }
    void dropActiveSession(int) { ++drops; active = nullptr; }
    void sendSystemMessage(const StringIdChatParameter& message) { ++messages; lastDI = message.di; }
    String getFirstName() const { return "Player"; }
};
struct StructureObject : SceneObject {
    uint64 deedID = 0, waypointID = 0;
    void setDeedObjectID(uint64 value) { deedID = value; }
    void setWaypointID(uint64 value) { waypointID = value; }
    String getDisplayedName() const { return "House"; }
    String getObjectName() const { return "House"; }
    bool isBuildingObject() const { return false; }
};
struct BuildingObject : StructureObject {
    SceneObject* getSignObject() { return nullptr; }
    bool isCivicStructure() const { return false; }
    bool isCommercialStructure() const { return false; }
};
struct StructureDeed : SceneObject {
    bool persistent = true;
    int notified = 0;
    String templateName = "house.iff";
    String getGeneratedObjectTemplate() const { return templateName; }
    bool isPersistent() const { return persistent; }
    void notifyStructurePlaced(CreatureObject*, StructureObject*) { ++notified; }
};
struct StructureManager {
    static StructureManager* current;
    AccountLotLedger ledger;
    int capacity = 10, reserves = 0, releases = 0, placements = 0;
    bool failPlacement = false, throwPlacement = false;
    StructureObject* placed = nullptr;
    uint64 receivedToken = 0;
    static StructureManager* instance() { return current; }
    uint64 reserveAccountLots(PlayerObject* player, int lots) {
        ++reserves;
        return player ? ledger.reserve(player->account, capacity, lots) : 0;
    }
    void releaseAccountLots(uint64 token) { ++releases; ledger.release(token); }
    StructureObject* placeStructure(CreatureObject* player, const String&, float, float, int, int, uint64 token) {
        ++placements;
        receivedToken = token;
        if (throwPlacement) throw std::runtime_error("placement failure");
        if (failPlacement) return nullptr;
        auto structure = makeObject<StructureObject>();
        if (!ledger.setStructure(structure->id, player->ghost.owner, TemplateManager::current->definition.lots, token))
            return nullptr;
        placed = structure;
        return structure;
    }
};
StructureManager* StructureManager::current = nullptr;
int PlayerObject::getLotsRemaining() { return StructureManager::current->ledger.remaining(account, StructureManager::current->capacity); }
struct TrxCode { static constexpr int STRUCTUREDEED = 1; };
struct TransactionLog {
    template<class... Args> TransactionLog(Args...) {}
    void addState(const char*, const String&) {}
};
struct Task;
std::vector<Task*> tasks;
bool throwOnSchedule = false;
struct Task {
    int delay = -1;
    Task() { tasks.push_back(this); }
    virtual ~Task() = default;
    virtual void run() = 0;
    void schedule(int value) {
        if (throwOnSchedule) throw std::runtime_error("scheduling failure");
        delay = value;
    }
};
struct PlaceStructureSession : FacadeImplementation {
    Ref<CreatureObject*> creatureObject;
    Ref<StructureDeed*> deedObject;
    float positionX = 0, positionY = 0;
    int directionAngle = 0;
    uint64 lotReservation = 0;
    Ref<SceneObject*> constructionBarricade;
    Ref<Zone*> zone;
    Ref<ActiveArea*> temporaryNoBuildZone;
    int errors = 0;
    struct Self {
        PlaceStructureSession* value;
        PlaceStructureSession* getReferenceUnsafeStaticCast() { return value; }
    } _this{this};
    PlaceStructureSession(CreatureObject* player, StructureDeed* deed)
        : creatureObject(player), deedObject(deed), zone(player ? player->getZone() : nullptr) {}
    void initializeTransientMembers();
    int constructStructure(float, float, int);
    void placeTemporaryNoBuildZone(const SharedStructureObjectTemplate*);
    void removeTemporaryNoBuildZone();
    int completeSession();
    int cancelSession();
    void error(const char*) { ++errors; }
};
'''


TESTS = r'''
int checks = 0;
void check(bool result, const char* description) {
    if (!result) { std::cerr << "FAIL: " << description << '\n'; std::exit(1); }
    ++checks;
}
struct Fixture {
    StructureManager manager;
    TemplateManager templates;
    ObjectManager objectManager;
    Zone zone;
    CreatureObject player;
    StructureDeed deed;
    PlaceStructureSession session;
    Fixture() : session(&player, &deed) {
        StructureManager::current = &manager;
        TemplateManager::current = &templates;
        ObjectManager::current = &objectManager;
        manager.ledger.registerOwner(11, 1);
        manager.ledger.registerOwner(12, 1);
        manager.ledger.setReady(true);
        player.worldZone = &zone;
        session.zone = &zone;
        player.active = &session;
        deed.parent = &player.inventory;
        deed.id = 101;
        throwOnSchedule = false;
    }
    ~Fixture() {
        for (auto task : tasks) delete task;
        tasks.clear();
        objects.clear();
    }
    int remaining() { return player.ghost.getLotsRemaining(); }
    int begin() { return session.constructStructure(12, 34, 90); }
    void detach() { deed.destroyObjectFromWorld(true); }
};

void reservationAndOverlap() {
    Fixture f;
    check(f.begin() == 0, "valid placement begins");
    check(f.session.lotReservation != 0 && f.remaining() == 4, "begin reserves capacity before delayed construction");
    check(f.deed.parent == &f.player.inventory && f.deed.destroyed == 0, "begin leaves deed in inventory for caller to detach");
    check(f.session.temporaryNoBuildZone != nullptr && f.session.constructionBarricade != nullptr, "valid begin creates temporary world objects");
    check(tasks.size() == 1 && tasks[0]->delay == 18000, "timer keeps per-lot construction duration");
    CreatureObject sibling;
    sibling.ghost.owner = 12;
    sibling.worldZone = &f.zone;
    StructureDeed otherDeed;
    otherDeed.parent = &sibling.inventory;
    PlaceStructureSession second(&sibling, &otherDeed);
    sibling.active = &second;
    f.templates.definition.lots = 5;
    check(second.constructStructure(1, 2, 3) != 0, "sibling cannot overspend pending account reservation");
    check(otherDeed.parent == &sibling.inventory && otherDeed.destroyed == 0, "denial retains original deed");
    check(sibling.messages == 1 && sibling.lastDI == 5, "denial reports required lots");
    check(tasks.size() == 1 && f.zone.server.areaCreates == 1, "denial does not start construction or create area");
    check(f.remaining() == 4 && second.lotReservation == 0, "denial preserves first reservation only");
    f.session.cancelSession();
    check(f.remaining() == 10, "cancelling pending placement makes capacity available");
}

void zeroLotAndInvalidBegin() {
    {
        Fixture f;
        f.manager.capacity = 0;
        f.templates.definition.lots = 0;
        f.templates.definition.marker = "";
        check(f.begin() == 0 && f.session.lotReservation != 0, "zero-lot structure receives valid reservation at zero capacity");
        check(tasks.size() == 1 && tasks[0]->delay == 100, "markerless zero-lot structure uses fallback timer");
        f.detach();
        tasks[0]->run();
        check(f.manager.placed != nullptr && f.remaining() == 0, "zero-lot completion commits without consuming capacity");
    }
    for (int mode = 0; mode < 4; ++mode) {
        Fixture f;
        if (mode == 0) f.templates.missing = true;
        if (mode == 1) f.session.deedObject = nullptr;
        if (mode == 2) f.session.zone = nullptr;
        if (mode == 3) f.player.missingGhost = true;
        check(f.begin() != 0, "invalid begin rejected");
        check(f.remaining() == 10 && f.session.lotReservation == 0, "invalid begin leaves no reservation");
        check(f.deed.parent == &f.player.inventory && tasks.empty(), "invalid begin preserves deed and schedules nothing");
    }
}

void setupFailures() {
    for (int mode = 0; mode < 5; ++mode) {
        Fixture f;
        if (mode == 0) f.zone.server.failArea = true;
        if (mode == 1) f.zone.failAreaTransfer = true;
        if (mode == 2) f.zone.failMarkerTransfer = true;
        if (mode == 3) f.objectManager.throwOnCreate = true;
        if (mode == 4) throwOnSchedule = true;
        bool threw = false;
        int result = 0;
        try { result = f.begin(); } catch (const std::runtime_error&) { threw = true; }
        check(mode >= 3 ? threw : result != 0, "setup failure rejects or rethrows");
        check(f.remaining() == 10 && f.manager.releases == 1, "setup failure releases reserved lots once");
        check(f.session.lotReservation == 0 && f.player.active == nullptr, "setup failure clears active placement");
        check(f.session.temporaryNoBuildZone == nullptr && f.session.constructionBarricade == nullptr, "setup failure clears temporary handles");
        check(f.deed.parent == &f.player.inventory && f.player.inventory.transfers == 0, "setup failure leaves undetached deed alone");
        for (const auto& object : objects) check(object->destroyed == 1 && object->worldZone == nullptr, "created temporary object removed exactly once");
        f.session.cancelSession();
        check(f.manager.releases == 1, "failed setup cancellation is idempotent");
    }
}

void successfulCompletion() {
    Fixture f;
    check(f.begin() == 0, "successful scenario begins");
    auto token = f.session.lotReservation;
    auto area = f.session.temporaryNoBuildZone.get();
    auto marker = f.session.constructionBarricade.get();
    f.detach();
    tasks[0]->run();
    check(f.manager.placements == 1 && f.manager.receivedToken == token, "completion passes original reservation to placement");
    check(f.manager.placed != nullptr && f.manager.placed->deedID == f.deed.id, "completion binds detached deed to structure");
    check(f.remaining() == 4 && f.session.lotReservation == 0, "commit consumes reservation and preserves owned usage");
    check(f.player.active == nullptr && f.player.drops == 1, "successful completion clears exact session");
    check(f.deed.parent == nullptr && f.player.inventory.transfers == 0, "successful cleanup never returns consumed deed");
    check(area->destroyed == 1 && marker->destroyed == 1, "successful completion removes construction objects");
    check(f.deed.notified == 1 && f.player.ghost.waypoints == 1 && f.zone.server.chat.messages == 1, "completion retains notification waypoint and mail");
    f.session.cancelSession();
    tasks[0]->run();
    check(f.manager.placements == 1 && f.remaining() == 4, "late cancel and repeated timer cannot refund or place again");
    check(f.player.inventory.transfers == 0 && area->destroyed == 1 && marker->destroyed == 1, "late cleanup does not restore successful deed or repeat destruction");
}

void completionFailures() {
    for (int mode = 0; mode < 2; ++mode) {
        Fixture f;
        f.begin();
        f.detach();
        auto area = f.session.temporaryNoBuildZone.get();
        auto marker = f.session.constructionBarricade.get();
        f.manager.failPlacement = mode == 0;
        f.manager.throwPlacement = mode == 1;
        bool threw = false;
        try { tasks[0]->run(); } catch (const std::runtime_error&) { threw = true; }
        check(threw == (mode == 1), "manager exception propagates after cleanup");
        check(f.remaining() == 10 && f.session.lotReservation == 0, "failed completion releases reservation");
        check(f.deed.parent == &f.player.inventory && f.player.inventory.transfers == 1, "failed completion returns detached persistent deed");
        check(f.player.inventory.overflowAllowed, "deed recovery permits inventory overflow");
        check(f.player.active == nullptr && area->destroyed == 1 && marker->destroyed == 1, "failed completion clears session and construction objects");
        check(f.deed.notified == 0 && f.player.ghost.waypoints == 0, "failed completion sends no success effects");
    }
}

void cancellationAndDeedOwnership() {
    for (int mode = 0; mode < 5; ++mode) {
        Fixture f;
        f.begin();
        f.detach();
        SceneObject foreignInventory;
        if (mode == 1) f.deed.parent = &foreignInventory;
        if (mode == 2) f.deed.persistent = false;
        if (mode == 3) f.deed.worldZone = &f.zone;
        if (mode == 4) f.deed.parent = &f.player.inventory;
        auto area = f.session.temporaryNoBuildZone.get();
        auto marker = f.session.constructionBarricade.get();
        // Logout removes active sessions before invoking their cancellation.
        f.player.active = nullptr;
        f.session.cancelSession();
        f.session.cancelSession();
        tasks[0]->run();
        check(f.remaining() == 10 && f.manager.releases == 1, "logout cancellation releases lots once");
        check(f.manager.placements == 0 && f.player.drops == 0, "cancelled logout timer never completes or drops another session");
        check(area->destroyed == 1 && marker->destroyed == 1, "repeated cancellation destroys temporary objects once");
        check(f.player.inventory.transfers == (mode == 0 ? 1 : 0), "only detached persistent deed is returned");
        if (mode == 1) check(f.deed.parent == &foreignInventory, "foreign inventory retains transferred deed");
        if (mode == 2) check(!f.deed.persistent && f.deed.parent == nullptr, "deleted deed is not resurrected");
        if (mode == 3) check(f.deed.worldZone == &f.zone, "deed placed in world is not stolen back");
    }
}

void staleTasksAndInvalidCompletion() {
    {
        Fixture f;
        f.begin();
        f.detach();
        StructureDeed nextDeed;
        nextDeed.parent = &f.player.inventory;
        PlaceStructureSession next(&f.player, &nextDeed);
        f.player.active = &next;
        f.templates.definition.lots = 4;
        check(next.constructStructure(50, 60, 0) == 0 && f.remaining() == 0, "new session can reserve only remaining account capacity");
        auto nextToken = next.lotReservation;
        tasks[0]->run();
        check(f.player.active == &next && next.lotReservation == nextToken, "stale timer preserves newer active session and its reservation");
        check(f.manager.placements == 0 && f.remaining() == 6, "stale timer cancels only old placement");
        check(f.deed.parent == &f.player.inventory && nextDeed.parent == &f.player.inventory, "stale cancellation restores only old detached deed");
        nextDeed.destroyObjectFromWorld(true);
        tasks[1]->run();
        check(f.manager.placements == 1 && f.manager.placed->deedID == nextDeed.id, "new timer completes its own session");
        check(f.remaining() == 6, "new structure cost survives both timer cleanups");
    }
    for (int mode = 0; mode < 5; ++mode) {
        Fixture f;
        f.begin();
        f.detach();
        Zone otherZone;
        SceneObject foreignInventory;
        if (mode == 0) f.player.worldZone = &otherZone;
        if (mode == 1) f.deed.parent = &foreignInventory;
        if (mode == 2) f.deed.persistent = false;
        if (mode == 3) f.deed.worldZone = &f.zone;
        if (mode == 4) f.player.active = nullptr;
        tasks[0]->run();
        check(f.manager.placements == 0 && f.remaining() == 10, "invalid completion cannot create structure and releases capacity");
        check(f.session.lotReservation == 0 && f.player.active == nullptr, "invalid completion clears exact session");
    }
    {
        Fixture f;
        f.begin();
        f.detach();
        f.session.creatureObject = nullptr;
        auto expiredCreatureTask = new StructureConstructionCompleteTask(nullptr, &f.session);
        expiredCreatureTask->run();
        check(f.remaining() == 10 && f.manager.placements == 0, "expired creature timer releases pending capacity");
        check(f.deed.parent == nullptr && f.player.inventory.transfers == 0, "expired creature cannot restore deed through stale player");
        auto expiredSessionTask = new StructureConstructionCompleteTask(&f.player, nullptr);
        expiredSessionTask->run();
        check(f.manager.placements == 0, "expired session timer is harmless");
    }
}

void restoredSessionCannotReleaseNewReservation() {
    Fixture f;
    auto newToken = f.manager.ledger.reserve(1, 10, 6);
    check(newToken != 0 && f.remaining() == 4, "new process allocates a live reservation");
    // A saved old session can contain the same numeric token from a prior run.
    f.session.lotReservation = newToken;
    f.detach();
    f.session.initializeTransientMembers();
    check(f.session.transientInitializations == 1, "restore calls base transient initializer");
    check(f.session.lotReservation == 0, "restore discards the prior process reservation token");
    check(f.session.deedObject == &f.deed, "restore retains the deed for later cancellation recovery");
    check(f.remaining() == 4 && f.manager.releases == 0, "restore does not release a current process reservation");
    f.session.completeSession();
    check(f.manager.placements == 0 && f.session.lotReservation == 0, "restored session cannot resume unreserved construction");
    check(f.player.active == nullptr && f.deed.parent == &f.player.inventory, "restored session cancellation recovers detached deed");
    check(f.remaining() == 4 && f.manager.releases == 0, "restored cancellation preserves coincident live reservation");
    check(f.manager.ledger.setStructure(888, 12, 6, newToken), "unrelated live reservation remains valid for its owner");
    check(f.remaining() == 4, "live reservation commits without losing its account charge");
}

int main() {
    reservationAndOverlap();
    zeroLotAndInvalidBegin();
    setupFailures();
    successfulCompletion();
    completionFailures();
    cancellationAndDeedOwnership();
    staleTasksAndInvalidCompletion();
    restoredSessionCannotReleaseNewReservation();
    std::cout << "Passed " << checks << " account-lot placement lifecycle checks\n";
}
'''


def main():
    session = SESSION.read_text()
    schema = SESSION_IDL.read_text()
    assert re.search(r"protected\s+transient\s+unsigned long\s+lotReservation\s*;", schema), "Reservation tokens must not be serialized"
    assert "public native void initializeTransientMembers();" in schema, "Restore must invoke the session transient initializer"
    signatures = (
        "void PlaceStructureSessionImplementation::initializeTransientMembers(",
        "int PlaceStructureSessionImplementation::constructStructure(",
        "void PlaceStructureSessionImplementation::placeTemporaryNoBuildZone(",
        "void PlaceStructureSessionImplementation::removeTemporaryNoBuildZone(",
        "int PlaceStructureSessionImplementation::completeSession(",
        "int PlaceStructureSessionImplementation::cancelSession(",
    )
    methods = "\n\n".join(function(session, signature) for signature in signatures)
    methods = methods.replace("PlaceStructureSessionImplementation::", "PlaceStructureSession::")
    task = function(TASK.read_text(), "class StructureConstructionCompleteTask") + ";"
    harness = MOCKS + "\n" + task + "\n" + methods + "\n" + TESTS
    with tempfile.TemporaryDirectory(prefix="account-lot-placement-", dir=CORE / "bin") as directory:
        source = Path(directory) / "placement.cpp"
        executable = Path(directory) / "placement"
        source.write_text(harness)
        subprocess.run(
            shlex.split(os.environ.get("CXX", "g++"))
            + ["-std=c++17", "-Wall", "-Wextra", "-pedantic", "-pthread",
               "-I", str(LEDGER.parent), str(source), "-o", str(executable)],
            check=True,
        )
        subprocess.run([str(executable)], check=True)
    print("Passed 2 placement session persistence schema checks")


if __name__ == "__main__":
    main()
