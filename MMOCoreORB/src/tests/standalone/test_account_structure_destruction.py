#!/usr/bin/env python3
"""Exercise extracted destruction sessions, callbacks, and redeed transaction.

This compiles only a standard-library mock harness, never Core3/engine3. Input
response fields come from the actual input-box declarations. Real reference
lifetimes, locking, task execution, persistence, GCW destruction, and client
delivery still require integration testing. Temporary files stay under bin and
are removed.
"""
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

CORE = Path(__file__).resolve().parents[3]
SESSION = CORE / "src/server/zone/objects/player/sessions/DestroyStructureSessionImplementation.cpp"
MANAGER = CORE / "src/server/zone/managers/structure/StructureManager.cpp"
CALLBACKS = CORE / "src/server/zone/objects/player/sui/callbacks"
INPUT_BOX = CORE / "src/server/zone/objects/player/sui/inputbox/SuiInputBoxImplementation.cpp"
PLAYER = CORE / "src/server/zone/objects/player/PlayerObjectImplementation.cpp"


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


MOCKS = r'''
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using uint64 = std::uint64_t;
using uint32 = std::uint32_t;
struct String : std::string {
    using std::string::string;
    String(const std::string& value) : std::string(value) {}
    bool isEmpty() const { return empty(); }
    char charAt(int index) const { return at(index); }
    String toString() const { return *this; }
};
using UnicodeString = String;
struct StringBuffer : std::ostringstream { String toString() const { return str(); } };
template<class T> struct Vector : std::vector<T> { T get(int i) { return this->at(i); } };
struct Integer { static int valueOf(const String& value) { return std::stoi(value); } };
struct System { static int random(int) { return 123456; } };
#define STRING_HASHCODE(value) 1
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
struct StructureDeed;
struct StructureObject;
std::function<void()> onDeedLock;
struct Locker {
    template<class... Args> Locker(Args...) {}
    Locker(Ref<StructureDeed*>, Ref<StructureObject*>) {
        if (onDeedLock) { auto callback = onDeedLock; onDeedLock = {}; callback(); }
    }
};
struct CreatureObject;
struct DestroyStructureSession;
struct Zone;
struct ZoneServer;
struct SuiBox;
struct SceneObject {
    virtual ~SceneObject() = default;
    uint64 id = 100;
    SceneObject* parent = nullptr;
    Zone* zone = nullptr;
    bool transferFails = false;
    int transfers = 0, broadcasts = 0, detached = 0, count = 0, capacity = 80;
    uint64 getObjectID() const { return id; }
    int getCountableObjectsRecursive() const { return count; }
    int getContainerVolumeLimit() const { return capacity; }
    bool transferObject(SceneObject* obj, int, bool, bool = false) {
        ++transfers; if (transferFails) return false; obj->parent = this; return true;
    }
    void broadcastObject(SceneObject*, bool) { ++broadcasts; }
    void destroyObjectFromWorld(bool) { parent = nullptr; zone = nullptr; ++detached; }
    void destroyObjectFromDatabase(bool) {}
};
struct PlayerObject {
    bool staff = false;
    int boxes = 0;
    Vector<Ref<SuiBox*>> suiBoxes;
    std::vector<uint32> closedBoxes;
    bool isStaff() const { return staff; }
    void addSuiBox(SuiBox* box) { ++boxes; suiBoxes.push_back(box); }
    void removeSuiBox(uint32 boxID, bool closeWindow);
    void recoverDestructionAfterLogin(CreatureObject* playerCreature);
};
struct SessionFacade { virtual ~SessionFacade() = default; };
struct SessionFacadeType { static constexpr int DESTROYSTRUCTURE = 1, OTHER = 2; };
struct ObjectFlag { static constexpr int OVERT = 1; };
struct CreatureObject : SceneObject {
    PlayerObject ghost;
    SceneObject inventory;
    bool player = true, missingGhost = false, missingInventory = false;
    SessionFacade* active = nullptr;
    SessionFacade* unrelatedActive = nullptr;
    ZoneServer* server = nullptr;
    std::vector<String> messages;
    int drops = 0;
    uint32 accountID = 7;
    bool isPlayerCreature() const { return player; }
    Ref<PlayerObject*> getPlayerObject() { return missingGhost ? nullptr : &ghost; }
    Ref<SessionFacade*> getActiveSession(int type) { return type == SessionFacadeType::DESTROYSTRUCTURE ? active : unrelatedActive; }
    bool containsActiveSession(int type) { return getActiveSession(type) != nullptr; }
    void addActiveSession(int type, SessionFacade* session) {
        (type == SessionFacadeType::DESTROYSTRUCTURE ? active : unrelatedActive) = session;
    }
    void dropActiveSession(int type) {
        ++drops; (type == SessionFacadeType::DESTROYSTRUCTURE ? active : unrelatedActive) = nullptr;
    }
    Ref<SceneObject*> getSlottedObject(const char*) { return missingInventory ? nullptr : &inventory; }
    ZoneServer* getZoneServer() { return server; }
    void sendSystemMessage(const String& message) { messages.push_back(message); }
    void sendMessage(int) {}
};
struct StructureObject : SceneObject {
    bool allowed = true, pending = false, redeedable = true, gcw = false;
    int pvp = 0;
    int maintenance = 1000, redeedCost = 200;
    uint64 deedID = 200;
    uint64 ownerID = 100;
    uint32 ownerAccountID = 7;
    String reason;
    Zone* getZone() { return zone; }
    bool isPendingDestruction() const { return pending; }
    void setPendingDestruction(bool value) { pending = value; }
    bool isOwnedByAccount(CreatureObject* player) const {
        return allowed && (player->id == ownerID || (player->accountID != 0 && player->accountID == ownerAccountID));
    }
    String getRedeedMessage() const { return reason; }
    String getDisplayedName() const { return "House"; }
    bool isRedeedable() const { return redeedable; }
    int getSurplusMaintenance() const { return maintenance; }
    int getSurplusPower() const { return 300; }
    int getRedeedCost() const { return redeedCost; }
    int getMaxCondition() const { return 100; }
    int getConditionDamage() const { return 0; }
    uint64 getDeedObjectID() const { return deedID; }
    void setDeedObjectID(uint64 id) { deedID = id; }
    bool isGCWBase() const { return gcw; }
    int getPvpStatusBitmask() const { return pvp; }
    bool isTurret() const { return false; }
    bool isMinefield() const { return false; }
    bool isScanner() const { return false; }
};
struct BuildingObject : StructureObject {};
struct InstallationObject : StructureObject {};
struct HarvesterObject : InstallationObject {
    bool isSelfPowered() const { return false; }
    void setSelfPowered(bool) {}
};
struct StructureDeed : SceneObject {
    int maintenance = 0, power = 0;
    void setSurplusMaintenance(int value) { maintenance = value; }
    void setSurplusPower(int value) { power = value; }
};
struct GCWManager {
    bool vulnerable = false;
    int calls = 0;
    bool isBaseVulnerable(BuildingObject*) const { return vulnerable; }
    void doBaseDestruction(StructureObject*);
};
struct Zone { GCWManager gcw; GCWManager* getGCWManager() { return &gcw; } };
struct ZoneServer {
    StructureDeed* deed = nullptr;
    Ref<SceneObject*> getObject(uint64 id) { return deed != nullptr && id == deed->id ? deed : nullptr; }
    Ref<SceneObject*> createObject(int, int) { return nullptr; }
};
struct SuiCallback {
    SuiCallback(ZoneServer*) {}
    virtual ~SuiCallback() = default;
};
uint32 nextBoxID = 0;
struct SuiBox {
    Ref<SceneObject*> usingObject;
    SuiCallback* callback = nullptr;
    uint32 boxID;
    SuiBox(CreatureObject* = nullptr) : boxID(++nextBoxID) {}
    virtual ~SuiBox() { delete callback; }
    Ref<SceneObject*> getUsingObject() { return usingObject; }
    void setUsingObject(SceneObject* object) { usingObject = object; }
    void setCallback(SuiCallback* value) { callback = value; }
    SuiCallback* getCallback() { return callback; }
    uint32 getBoxID() const { return boxID; }
    void setCancelButton(bool, const char*) {}
    void setOkButton(bool, const char*) {}
    void setPromptTitle(const String&) {}
    void setPromptText(const String&) {}
    void setMaxInputSize(int) {}
    void addMenuItem(const String&) {}
    int generateMessage() { return 0; }
};
void PlayerObject::removeSuiBox(uint32 boxID, bool closeWindow) {
    for (auto it = suiBoxes.begin(); it != suiBoxes.end(); ++it) {
        if (it->get() != nullptr && (*it)->getBoxID() == boxID) {
            if (closeWindow) closedBoxes.push_back(boxID);
            suiBoxes.erase(it);
            return;
        }
    }
}
struct SuiInputBox : SuiBox { using SuiBox::SuiBox; };
struct SuiListBox : SuiBox { using SuiBox::SuiBox; };
struct DestroyStructureSession : SessionFacade {
    Ref<CreatureObject*> creatureObject;
    Ref<StructureObject*> structureObject;
    uint32 destroyCode = 0;
    struct Self { DestroyStructureSession* value; DestroyStructureSession* getReferenceUnsafeStaticCast() { return value; } } _this{this};
    DestroyStructureSession(CreatureObject* player, StructureObject* structure) : creatureObject(player), structureObject(structure) {}
    bool isDestroyCode(uint32 code) const { return code == destroyCode; }
    StructureObject* getStructureObject() { return structureObject; }
    int initializeSession(); int sendDestroyCode(); int destroyStructure(); int cancelSession();
};
int queued = 0;
bool throwOnExecute = false;
struct DestroyStructureTask {
    StructureObject* structure;
    DestroyStructureTask(StructureObject* structure, bool) : structure(structure) {}
    void execute() {
        if (!structure->pending) throw std::runtime_error("destruction was not marked before scheduling");
        if (throwOnExecute) throw std::runtime_error("task scheduling failed");
        ++queued;
    }
};
struct DestroyFactionInstallationTask {
    DestroyFactionInstallationTask(InstallationObject*) {}
    void execute() {}
};
struct StructureManager {
    static StructureManager* current;
    ZoneServer* server = nullptr;
    static StructureManager* instance() { return current; }
    int destroyStructure(StructureObject*, bool = false);
    int redeedStructure(CreatureObject*);
};
StructureManager* StructureManager::current = nullptr;
void GCWManager::doBaseDestruction(StructureObject* structure) {
    ++calls; StructureManager::instance()->destroyStructure(structure, true);
}
struct TrxCode { static constexpr int STRUCTUREDEED = 1; };
struct TransactionLog {
    template<class... Args> TransactionLog(Args...) {}
    template<class T> void addState(const char*, T) {}
    void groupWith(TransactionLog&) {}
    std::ostringstream sink;
    std::ostringstream& abort() { return sink; }
};
'''

TESTS = r'''
int checks = 0;
void check(bool value, const char* message) {
    if (!value) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); } ++checks;
}
struct Fixture {
    Zone zone;
    ZoneServer server;
    CreatureObject player;
    BuildingObject structure;
    StructureDeed deed;
    StructureManager manager;
    DestroyStructureSession session{&player, &structure};
    Fixture() {
        deed.id = 200; server.deed = &deed; player.server = &server;
        structure.zone = &zone; player.active = &session;
        manager.server = &server; StructureManager::current = &manager;
        queued = 0; throwOnExecute = false; onDeedLock = {};
    }
    bool messaged(const char* text) {
        for (const auto& message : player.messages) if (message == text) return true;
        return false;
    }
};
int main() {
    for (int mode = 0; mode < 3; ++mode) {
        Fixture f;
        if (mode == 1) f.player.id = 101;
        f.session.sendDestroyCode();
        SuiBox box; box.setUsingObject(&f.structure);
        DestroyStructureCodeSuiCallback code(&f.server, &f.session);
        auto args = normalInputResponse(std::to_string(f.session.destroyCode));
        check(args.size() == 2, "normal input box response contains both declared properties");
        if (mode == 2) args.resize(1);
        code.run(&f.player, &box, 0, &args);
        check(queued == 1 && f.structure.pending && f.player.active == nullptr,
              "real two-property code response destroys for title owner and account alt; one-property response remains valid");
        check(f.deed.parent == &f.player.inventory && f.structure.deedID == 0, "valid response delivers the deed exactly once");
        code.run(&f.player, &box, 0, &args);
        check(queued == 1 && f.player.inventory.transfers == 1, "repeated response cannot destroy again or duplicate deed");
    }
    for (int mode = 0; mode < 8; ++mode) {
        Fixture f;
        if (mode == 1) f.structure.allowed = false;
        if (mode == 2) { f.structure.allowed = false; f.player.ghost.staff = true; }
        if (mode == 3) f.structure.pending = true;
        if (mode == 4) f.structure.zone = nullptr;
        if (mode == 5) f.player.missingGhost = true;
        if (mode == 6) f.player.player = false;
        if (mode == 7) f.structure.reason = "not_empty";
        check(canDestroyStructure(&f.player, &f.structure) == (mode == 0 || mode == 2), "account owner or staff eligible; invalid states rejected");
    }
    {
        Fixture f; f.player.active = nullptr;
        check(f.session.initializeSession() == 0 && f.player.active == &f.session, "valid owner session initializes");
        check(f.player.ghost.boxes == 1, "initial confirmation is generated");
        f.session.sendDestroyCode();
        check(f.session.destroyCode != 0 && f.player.ghost.boxes == 2, "second confirmation generates destruction code");
        f.structure.allowed = false;
        f.session.destroyStructure();
        check(queued == 0 && f.player.active == nullptr && f.deed.parent == nullptr, "ownership loss after dialog blocks destruction and deed delivery");
    }
    {
        Fixture f; f.structure.allowed = false;
        f.session.sendDestroyCode();
        check(f.session.destroyCode == 0 && f.player.active == nullptr, "ownership loss before code cancels session");
    }
    {
        Fixture f;
        DestroyStructureSession newer(&f.player, &f.structure);
        f.player.active = &newer;
        f.session.cancelSession(); f.session.destroyStructure();
        check(f.player.active == &newer && f.player.drops == 0 && queued == 0, "old session cannot cancel or execute newer session");
        SuiBox box; box.setUsingObject(&f.structure);
        DestroyStructureRequestSuiCallback request(&f.server, &f.session);
        DestroyStructureCodeSuiCallback code(&f.server, &f.session);
        auto args = normalInputResponse("000000");
        request.run(&f.player, &box, 0, &args); code.run(&f.player, &box, 0, &args);
        request.run(&f.player, &box, 1, &args); code.run(&f.player, &box, 1, &args);
        code.run(&f.player, &box, 0, nullptr);
        check(f.player.active == &newer && newer.destroyCode == 0 && queued == 0, "old dialog cannot accept or cancel new session for same structure");
    }
    {
        Fixture f;
        StructureObject other;
        SuiBox box; box.setUsingObject(&other);
        DestroyStructureRequestSuiCallback request(&f.server, &f.session);
        DestroyStructureCodeSuiCallback code(&f.server, &f.session);
        auto args = normalInputResponse("000000");
        request.run(&f.player, &box, 0, &args); code.run(&f.player, &box, 0, &args);
        check(f.session.destroyCode == 0 && queued == 0 && f.player.active == &f.session, "mismatched using object cannot act on session");
        box.setUsingObject(&f.structure);
        request.run(&f.player, &box, 0, &args);
        check(f.session.destroyCode != 0, "matching first confirmation requests code");
        args[0] = std::to_string(f.session.destroyCode);
        code.run(&f.player, &box, 0, &args);
        check(queued == 1 && f.structure.pending && f.player.active == nullptr, "matching correct code schedules exactly one destruction");
        check(f.deed.parent == &f.player.inventory && f.structure.deedID == 0, "account actor receives deed before deletion");
        check(f.deed.maintenance == 800 && f.deed.power == 300, "redeed preserves maintenance and power");
        f.manager.destroyStructure(&f.structure);
        check(queued == 1, "repeated destruction scheduling is rejected");
    }
    {
        const std::vector<String> invalidInputs = {
            "", "abcdef", "22345x", "4295190752", "223456suffix", "+223456", "-223456",
            " 223456", "223456 ", "22345", "0223456", "000000", "999999", "\xff\xff\xff\xff\xff\xff"
        };
        for (std::size_t mode = 0; mode < invalidInputs.size() + 2; ++mode) {
            Fixture f; f.session.sendDestroyCode();
            SuiBox box; box.setUsingObject(&f.structure);
            DestroyStructureCodeSuiCallback code(&f.server, &f.session);
            auto args = normalInputResponse(mode < invalidInputs.size() ? invalidInputs[mode] : "");
            args[1] = std::to_string(f.session.destroyCode);
            if (mode == invalidInputs.size()) args.clear();
            code.run(&f.player, &box, 0, mode == invalidInputs.size() + 1 ? nullptr : &args);
            check(queued == 0 && !f.structure.pending && f.deed.parent == nullptr && f.structure.deedID == f.deed.id,
                  "invalid, wrong, missing, or null first code cannot use second response property to destroy");
            check(f.player.active == nullptr && f.messaged("@player_structure:incorrect_destroy_code"),
                  "rejected code reports error and clears its session rather than stranding pending destruction");
            DestroyStructureSession retry(&f.player, &f.structure);
            check(retry.initializeSession() == 0 && f.player.active == &retry, "a fresh destroy attempt starts immediately after rejected input");
            retry.cancelSession();
        }
    }
    for (int mode = 0; mode < 2; ++mode) {
        Fixture f; f.session.sendDestroyCode();
        SuiBox box; box.setUsingObject(&f.structure);
        DestroyStructureCodeSuiCallback code(&f.server, &f.session);
        auto args = normalInputResponse(std::to_string(f.session.destroyCode));
        code.run(&f.player, &box, 1, mode == 0 ? &args : nullptr);
        check(queued == 0 && f.player.active == nullptr && !f.structure.pending, "Cancel clears current session without destroying even with correct code");
        check(!f.messaged("@player_structure:incorrect_destroy_code"), "Cancel is not reported as an incorrect code");
    }
    for (int mode = 0; mode < 2; ++mode) {
        Fixture f; f.session.sendDestroyCode();
        SuiBox box; box.setUsingObject(&f.structure);
        DestroyStructureCodeSuiCallback code(&f.server, &f.session);
        auto args = normalInputResponse(std::to_string(f.session.destroyCode));
        if (mode == 0) { f.player.id = 101; f.player.accountID = 8; }
        else { f.structure.ownerID = 102; f.structure.ownerAccountID = 8; }
        code.run(&f.player, &box, 0, &args);
        check(queued == 0 && f.player.active == nullptr && f.deed.parent == nullptr, "valid code cannot bypass lost account ownership");
    }
    for (int mode = 0; mode < 6; ++mode) {
        Fixture f;
        if (mode == 0) f.structure.pending = true;
        if (mode == 1) f.structure.allowed = false;
        if (mode == 2) f.structure.zone = nullptr;
        if (mode == 3) f.player.inventory.count = f.player.inventory.capacity;
        if (mode == 4) f.player.inventory.transferFails = true;
        if (mode == 5) throwOnExecute = true;
        bool threw = false;
        try { f.manager.redeedStructure(&f.player); } catch (const std::runtime_error&) { threw = true; }
        check(threw == (mode == 5), "scheduling exception propagates after rollback");
        check(queued == 0 && f.structure.deedID == f.deed.id, "failed redeed preserves structure deed and schedules no deletion");
        check(f.deed.parent == nullptr && f.player.active == nullptr, "failed redeed leaves no inventory deed or active session");
        check(f.structure.pending == (mode == 0), "enqueue failure clears only its own pending marker");
        check(!f.messaged("@player_structure:deed_reclaimed"), "failed redeed never reports success");
        if (mode >= 4) check(f.messaged("@player_structure:deed_reclaimed_failed"), "delivery or scheduling failure reports failure");
        if (mode == 5) check(f.deed.detached == 1, "scheduling failure rolls delivered deed back out of inventory");
    }
    {
        Fixture f; f.structure.redeedable = false;
        f.session.destroyStructure();
        check(queued == 1 && f.structure.pending && f.deed.parent == nullptr, "nonredeedable structure schedules destruction without giving deed");
        check(f.messaged("@player_structure:structure_destroyed"), "nonredeedable success retains message");
    }
    for (int mode = 0; mode < 4; ++mode) {
        Fixture f;
        onDeedLock = [&] {
            if (mode == 0) f.structure.redeedable = false;
            if (mode == 1) f.structure.reason = "not_empty";
            if (mode == 2) { f.structure.maintenance = 1500; f.structure.redeedCost = 500; }
            if (mode == 3) f.structure.allowed = false;
        };
        f.manager.redeedStructure(&f.player);
        check(queued == (mode == 2 ? 1 : 0), "deed lock reacquisition revalidates eligibility and ownership");
        check(f.player.inventory.transfers == (mode == 2 ? 1 : 0), "stale eligibility cannot move deed or reward items");
        if (mode == 2) check(f.deed.maintenance == 1000, "redeed uses current maintenance and cost after lock wait");
        else check(f.structure.deedID == f.deed.id && f.player.active == nullptr, "changed structure is retained and confirmation cancelled");
        if (mode == 1) check(f.messaged("@player_structure:not_empty"), "changed contents report current blocking message");
    }
    {
        Fixture f; f.structure.allowed = false; f.player.ghost.staff = true;
        f.session.destroyStructure();
        check(queued == 1 && f.deed.parent == &f.player.inventory, "existing staff override can redeed another account structure");
    }
    for (int mode = 0; mode < 3; ++mode) {
        Fixture f;
        f.structure.gcw = true; f.structure.pvp = ObjectFlag::OVERT;
        f.zone.gcw.vulnerable = true;
        if (mode == 1) f.structure.pvp = 0;
        if (mode == 2) f.player.ghost.staff = true;
        f.session.destroyStructure();
        check(f.zone.gcw.calls == (mode == 0 ? 0 : 1), "GCW vulnerability blocks nonstaff overt destruction but preserves other existing rules");
        check(queued == (mode == 0 ? 0 : 1), "accepted GCW destruction reaches marked scheduling path");
        DestroyStructureSession second(&f.player, &f.structure);
        f.player.active = &second;
        second.destroyStructure();
        check(queued == (mode == 0 ? 0 : 1), "two account characters cannot queue repeated GCW destruction");
    }
    {
        Fixture f;
        SessionFacade unrelated;
        f.player.addActiveSession(SessionFacadeType::OTHER, &unrelated);
        f.player.ghost.recoverDestructionAfterLogin(&f.player);
        check(f.player.active == nullptr && f.player.ghost.suiBoxes.empty(), "login drops orphan destruction session even without a remaining dialog");
        check(f.player.getActiveSession(SessionFacadeType::OTHER) == &unrelated, "login preserves unrelated active session");
        check(queued == 0 && !f.structure.pending && f.deed.parent == nullptr, "login cleanup never destroys or returns a deed");
        DestroyStructureSession retry(&f.player, &f.structure);
        check(retry.initializeSession() == 0 && f.player.active == &retry, "login recovery allows a new destruction attempt");
        retry.cancelSession();
    }
    for (int sessionPresent = 0; sessionPresent < 2; ++sessionPresent) {
        Fixture f;
        if (!sessionPresent) f.player.active = nullptr;
        SessionFacade unrelated;
        f.player.addActiveSession(SessionFacadeType::OTHER, &unrelated);
        SuiBox ordinaryBefore, request1, code1, request2, code2, ordinaryAfter, noCallback;
        ordinaryBefore.setCallback(new SuiCallback(&f.server));
        ordinaryAfter.setCallback(new SuiCallback(&f.server));
        request1.setCallback(new DestroyStructureRequestSuiCallback(&f.server, &f.session));
        request2.setCallback(new DestroyStructureRequestSuiCallback(&f.server, &f.session));
        code1.setCallback(new DestroyStructureCodeSuiCallback(&f.server, &f.session));
        code2.setCallback(new DestroyStructureCodeSuiCallback(&f.server, &f.session));
        request1.setUsingObject(&f.structure); code1.setUsingObject(&f.structure);
        for (SuiBox* box : {&ordinaryBefore, &request1, &code1, &request2, &code2, &ordinaryAfter, &noCallback})
            f.player.ghost.addSuiBox(box);
        f.player.ghost.recoverDestructionAfterLogin(&f.player);
        check(f.player.active == nullptr && f.player.getActiveSession(SessionFacadeType::OTHER) == &unrelated,
              "dialog cleanup drops only destruction session");
        check(f.player.ghost.suiBoxes.size() == 3 && f.player.ghost.suiBoxes[0] == &ordinaryBefore
              && f.player.ghost.suiBoxes[1] == &ordinaryAfter && f.player.ghost.suiBoxes[2] == &noCallback,
              "login removes both destruction dialog types and retains unrelated or callback-free windows");
        check(f.player.ghost.closedBoxes == std::vector<uint32>({code2.boxID, request2.boxID, code1.boxID, request1.boxID}),
              "reverse removal closes every adjacent destruction dialog without skipping or closing unrelated windows");
        f.player.ghost.recoverDestructionAfterLogin(&f.player);
        check(f.player.ghost.suiBoxes.size() == 3 && f.player.ghost.closedBoxes.size() == 4 && f.player.active == nullptr,
              "cleanup with no destruction session is idempotent");
        DestroyStructureSession retry(&f.player, &f.structure);
        check(retry.initializeSession() == 0 && f.player.active == &retry, "fresh confirmation starts after stale login windows are removed");
        auto args = normalInputResponse("223456");
        auto oldRequest = dynamic_cast<DestroyStructureRequestSuiCallback*>(request1.getCallback());
        auto oldCode = dynamic_cast<DestroyStructureCodeSuiCallback*>(code1.getCallback());
        for (uint32 event : {0u, 1u}) {
            oldRequest->run(&f.player, &request1, event, &args);
            oldCode->run(&f.player, &code1, event, &args);
        }
        check(f.player.active == &retry && retry.destroyCode == 0 && queued == 0,
              "late pre-login callbacks cannot advance, cancel, or destroy a new session");
        retry.cancelSession();
    }
    {
        Fixture f; f.player.active = nullptr;
        f.structure.pending = true;
        f.player.ghost.recoverDestructionAfterLogin(&f.player);
        f.player.ghost.recoverDestructionAfterLogin(&f.player);
        check(f.player.active == nullptr && f.player.ghost.suiBoxes.empty() && f.player.ghost.closedBoxes.empty(),
              "login without a session or dialogs has no dialog side effects");
        check(f.structure.pending && queued == 0, "login recovery preserves an already queued structure destruction marker");
    }
    std::cout << "Passed " << checks << " account structure destruction checks\n";
}
'''


def main(code_callback_source=None):
    # An in-memory prior callback can prove a regression without changing production.
    session, manager = SESSION.read_text(), MANAGER.read_text()
    callbacks = "\n".join(function(code_callback_source if code_callback_source is not None and name == "DestroyStructureCodeSuiCallback"
                                   else (CALLBACKS / (name + ".h")).read_text(), "class " + name) + ";"
                          for name in ("DestroyStructureRequestSuiCallback", "DestroyStructureCodeSuiCallback"))
    # Derive the response shape from the real ordinary input box, not callback assumptions.
    header_block = function(INPUT_BOX.read_text(), "BaseMessage* SuiInputBoxImplementation::generateMessage(")
    header_block = header_block.split("//Declare Body Settings:", 1)[0].split("} else {", 1)[1]
    headers = re.findall(r'addHeader\("([^"]+)", "([^"]+)"\);', header_block)
    assert headers == [("txtInput", "LocalText"), ("cmbInput", "SelectedText")], headers
    response_builder = """
Vector<UnicodeString> normalInputResponse(const String& code) {
    Vector<UnicodeString> response;
    response.resize(%d);
    response[%d] = code;
    return response;
}
""" % (len(headers), headers.index(("txtInput", "LocalText")))
    methods = function(session, "bool canDestroyStructure(") + "\n"
    methods += "\n".join(function(session, "int DestroyStructureSessionImplementation::" + name + "(")
                         for name in ("initializeSession", "sendDestroyCode", "destroyStructure", "cancelSession"))
    methods = methods.replace("DestroyStructureSessionImplementation::", "DestroyStructureSession::")
    methods += "\n" + function(manager, "int StructureManager::destroyStructure(")
    methods += "\n" + function(manager, "int StructureManager::redeedStructure(")
    notify_online = function(PLAYER.read_text(), "void PlayerObjectImplementation::notifyOnline(")
    cleanup_start = notify_online.index("playerCreature->dropActiveSession(SessionFacadeType::DESTROYSTRUCTURE);")
    cleanup_end = notify_online.index("\n\tmiliSecsSession = 0;", cleanup_start)
    assert cleanup_end < notify_online.index("//Resend all suis.")
    methods += "\nvoid PlayerObject::recoverDestructionAfterLogin(CreatureObject* playerCreature) {\n"
    methods += notify_online[cleanup_start:cleanup_end] + "\n}\n"
    harness = MOCKS + "\n" + callbacks + "\n" + methods + "\n" + response_builder + "\n" + TESTS
    with tempfile.TemporaryDirectory(prefix="account-structure-destruction-", dir=CORE / "bin") as directory:
        source, executable = Path(directory) / "destruction.cpp", Path(directory) / "destruction"
        source.write_text(harness)
        subprocess.run(shlex.split(os.environ.get("CXX", "g++")) + ["-std=c++11", "-Wall", "-Wextra",
                       "-pedantic-errors", str(source), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
