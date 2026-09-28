#!/usr/bin/env python3
"""Exercise actual helper deletion, opt-out and stale-store control flow.

Uses extracted production C++ with standard-library mocks. The ordinary pet
storage body after its ownership guard is mocked; no Core3 component or engine3
header is compiled. Real database persistence, locks and client state still
need in-game verification.
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
#include <functional>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using uint64 = uint64_t;
struct String: std::string {
    using std::string::string;
    String(std::string value): std::string(value) {}
    static String valueOf(uint64 value) { return std::to_string(value); }
};
#define STRING_HASHCODE(text) std::hash<std::string>{}(text)
std::vector<std::string> events;
template<class T> struct Ref {
    T value = nullptr;
    Ref() = default;
    Ref(T value): value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
    template<class U> Ref<U> castTo() const { return dynamic_cast<U>(value); }
};
template<class T> using Reference = Ref<T>;
template<class T> using ManagedReference = Ref<T>;
template<class T> using WeakReference = Ref<T>;
struct Locker { template<class... T> explicit Locker(T...) {} };
struct System { static int random(int) { return 0; } };
struct DirectorManager {
    std::map<std::string, uint64> data;
    static DirectorManager* instance() { static DirectorManager director; return &director; }
    void removeSharedMemoryValueIfEqual(const String& key, uint64 value) {
        auto found = data.find(key);
        if (found != data.end() && found->second == value) {
            data.erase(found);
            events.push_back("shared-memory");
        }
    }
};
struct CreatureObject;
struct AiAgent;
struct PetControlDevice;
struct Zone {};
struct ZoneServer {
    bool loading = false, shuttingDown = false;
    bool isServerLoading() const { return loading; }
    bool isServerShuttingDown() const { return shuttingDown; }
};
struct StringIdChatParameter {
    StringIdChatParameter(const char*, const char*) {}
    void setTT(const String&) {}
    void setTO(const String&) {}
};
struct SceneObject {
    virtual ~SceneObject() = default;
    uint64 id = 1, crc = 0;
    SceneObject* root = nullptr;
    SceneObject* parent = nullptr;
    Zone* localZone = nullptr;
    std::vector<SceneObject*> children;
    int worldDeletes = 0, dbDeletes = 0;
    virtual bool isPetControlDevice() const { return false; }
    virtual bool isShipControlDevice() const { return false; }
    virtual bool isHelperDroidObject() const { return false; }
    virtual bool isASubChildOf(CreatureObject*) const { return false; }
    SceneObject* getRootParent() { return root; }
    Ref<SceneObject*> getParent() { return parent; }
    Zone* getLocalZone() { return localZone; }
    uint64 getObjectID() const { return id; }
    uint64 getServerObjectCRC() const { return crc; }
    int getContainerObjectsSize() const { return children.size(); }
    Ref<SceneObject*> getContainerObject(int i) { return children.at(i); }
    String getDisplayedName() const { return "helper"; }
    String getGameObjectTypeStringID() const { return "droid"; }
    virtual void destroyObjectFromWorld(bool) { ++worldDeletes; events.push_back("device-world"); }
    virtual void destroyObjectFromDatabase(bool) { ++dbDeletes; events.push_back("device-db"); }
};
struct TangibleObject: SceneObject {};
struct PlayerObject {
    std::map<std::string, std::string> data;
    std::vector<AiAgent*> active;
    int programClears = 0, saves = 0;
    bool hasActivePet(AiAgent* pet) const {
        for (auto value : active) if (value == pet) return true;
        return false;
    }
    void removeDroidCommands() { ++programClears; events.push_back("programs"); }
    void setScreenPlayData(const String& screen, const String& key, const String& value) {
        data[screen + "/" + key] = value;
        events.push_back("opt-out");
    }
    void updateToDatabase() { ++saves; events.push_back("save-player"); }
};
struct CreatureObject: TangibleObject {
    ZoneServer* server = nullptr;
    PlayerObject* ghost = nullptr;
    Zone* zone = nullptr;
    SceneObject* datapad = nullptr;
    int messages = 0;
    ZoneServer* getZoneServer() { return server; }
    PlayerObject* getPlayerObject() { return ghost; }
    Zone* getZone() { return zone; }
    SceneObject* getSlottedObject(const char*) { return datapad; }
    void sendSystemMessage(const StringIdChatParameter&) { ++messages; events.push_back("message"); }
};
struct AiAgent: CreatureObject {
    bool helper = true;
    bool storeSucceeds = true;
    int stores = 0;
    PetControlDevice* device = nullptr;
    CreatureObject* linked = nullptr;
    bool isHelperDroidObject() const override { return helper; }
    Ref<PetControlDevice*> getControlDevice() { return device; }
    Ref<CreatureObject*> getLinkedCreature() { return linked; }
};
struct PetManager { enum { HELPERDROIDPET = 3 }; };
struct PetControlDevice: SceneObject {
    CreatureObject* owner = nullptr;
    TangibleObject* controlled = nullptr;
    int petType = PetManager::HELPERDROIDPET;
    bool detachSucceeds = true;
    bool isPetControlDevice() const override { return true; }
    bool isASubChildOf(CreatureObject* player) const override { return owner == player; }
    TangibleObject* getControlledObject() { return controlled; }
    int getPetType() const { return petType; }
    void destroyObjectFromWorld(bool notify) override {
        SceneObject::destroyObjectFromWorld(notify);
        if (detachSucceeds) owner = nullptr;
    }
    void destroyObjectFromDatabase(bool notify) override {
        if (controlled != nullptr) ++controlled->dbDeletes;
        SceneObject::destroyObjectFromDatabase(notify);
    }
};
struct ShipObject: TangibleObject {
    CreatureObject* owner = nullptr;
    uint64 droidID = 0;
    int clears = 0;
    Ref<CreatureObject*> getOwner() { return owner; }
    uint64 getShipDroidID() const { return droidID; }
    void setShipDroidID(uint64 value, bool) { droidID = value; ++clears; events.push_back("ship"); }
};
struct ShipControlDevice: SceneObject {
    ShipObject* ship = nullptr;
    bool isShipControlDevice() const override { return true; }
    TangibleObject* getControlledObject() { return ship; }
};
struct StorePetTask {
    WeakReference<CreatureObject*> play;
    WeakReference<AiAgent*> pt;
    int reschedules = 0;
    StorePetTask(CreatureObject* player, AiAgent* pet): play(player), pt(pet) {}
    void schedule(int) { ++reschedules; }
    void run();
};
struct Fixture {
    ZoneServer server;
    Zone zone;
    CreatureObject player, otherPlayer;
    PlayerObject ghost;
    SceneObject datapad;
    AiAgent pet;
    PetControlDevice device;
    ShipObject currentShip, storedShip, otherShip;
    ShipControlDevice currentControl, storedControl, otherControl;
    Fixture() {
        events.clear();
        DirectorManager::instance()->data = {{"1:HelperDroidID:", 2}, {"1:questProgress:", 7}};
        player.server = &server;
        player.ghost = &ghost;
        player.zone = &zone;
        player.datapad = &datapad;
        pet.device = &device;
        pet.id = 2;
        pet.localZone = &zone;
        device.owner = &player;
        device.controlled = &pet;
        device.id = 100;
        currentShip.owner = storedShip.owner = &player;
        otherShip.owner = &otherPlayer;
        currentShip.droidID = storedShip.droidID = otherShip.droidID = device.id;
        currentControl.ship = &currentShip;
        storedControl.ship = &storedShip;
        otherControl.ship = &otherShip;
        datapad.children = {&device, &currentControl, &storedControl, &otherControl};
        ghost.active = {&pet};
        ghost.data["HelperDroid/questProgress"] = "preserved";
    }
};
'''


CASES = r'''
int main() {
    int passed = 0;
    auto check = [&](bool result) { assert(result); ++passed; };
    {
        Fixture f;
        f.player.root = &f.currentShip;
        f.pet.root = &f.currentShip;
        f.pet.parent = &f.currentShip;
        check(HelperDroidCleanup::remove(&f.player, &f.device));
        check(f.currentShip.droidID == 0 && f.storedShip.droidID == 0 && f.otherShip.droidID == 100 &&
              f.currentShip.clears == 1 && f.ghost.programClears == 1);
        check(f.pet.stores == 1 && f.pet.localZone == nullptr && f.ghost.active.empty() &&
              f.device.worldDeletes == 1 && f.device.dbDeletes == 1 && f.pet.dbDeletes == 1);
        check(f.ghost.data.size() == 1 && f.ghost.data.at("HelperDroid/questProgress") == "preserved");
        check(events == std::vector<std::string>({"ship", "programs", "ship", "store", "device-world", "shared-memory", "device-db"}));
        check(DirectorManager::instance()->data == std::map<std::string, uint64>({{"1:questProgress:", 7}}));
        StorePetTask stale(&f.player, &f.pet);
        stale.run();
        check(f.pet.stores == 1); // An old queued helper store cannot run after deletion.
    }
    {
        Fixture f;
        f.player.root = &f.currentShip;
        f.currentShip.droidID = 999;
        check(HelperDroidCleanup::remove(&f.player, &f.device) && f.currentShip.droidID == 999 &&
              f.ghost.programClears == 0); // Do not strip a different droid's programs.
    }
    {
        Fixture f;
        f.pet.localZone = nullptr;
        f.ghost.active.clear();
        check(HelperDroidCleanup::remove(&f.player, &f.device) && f.pet.stores == 0 &&
              f.device.dbDeletes == 1 && f.storedShip.droidID == 0 && f.ghost.programClears == 0);
    }
    {
        Fixture f;
        DirectorManager::instance()->data["1:HelperDroidID:"] = 999;
        check(HelperDroidCleanup::remove(&f.player, &f.device) &&
              DirectorManager::instance()->data.at("1:HelperDroidID:") == 999);
    }
    for (int needsStorage = 0; needsStorage < 3; ++needsStorage) {
        Fixture f;
        f.pet.localZone = nullptr;
        f.ghost.active.clear();
        if (needsStorage == 0) f.pet.parent = &f.currentShip;
        if (needsStorage == 1) f.pet.linked = &f.player;
        if (needsStorage == 2) f.ghost.active = {&f.pet};
        check(HelperDroidCleanup::remove(&f.player, &f.device) && f.pet.stores == 1);
    }
    for (int invalid = 0; invalid < 7; ++invalid) {
        Fixture f;
        if (invalid == 0) f.server.loading = true;
        if (invalid == 1) f.server.shuttingDown = true;
        if (invalid == 2) f.player.server = nullptr;
        if (invalid == 3) f.player.zone = nullptr;
        if (invalid == 4) f.player.ghost = nullptr;
        if (invalid == 5) f.device.owner = &f.otherPlayer;
        TangibleObject invalidPet;
        if (invalid == 6) f.device.controlled = &invalidPet;
        check(!HelperDroidCleanup::remove(&f.player, &f.device) && events.empty() && f.device.dbDeletes == 0);
    }
    {
        Fixture f;
        f.pet.storeSucceeds = false;
        check(!HelperDroidCleanup::remove(&f.player, &f.device) && f.device.worldDeletes == 0 && f.device.dbDeletes == 0);
    }
    {
        Fixture f;
        f.device.detachSucceeds = false;
        check(!HelperDroidCleanup::remove(&f.player, &f.device) && f.device.dbDeletes == 0);
    }
    {
        Fixture f;
        f.device.controlled = nullptr;
        check(HelperDroidCleanup::remove(&f.player, &f.device) && f.device.dbDeletes == 1 && f.pet.stores == 0);
    }
    {
        Fixture f;
        f.device.petType = 0;
        check(HelperDroidCleanup::isHelperDevice(&f.device)); // Controlled-object fallback.
        f.pet.helper = false;
        check(!HelperDroidCleanup::isHelperDevice(&f.device));
        f.device.controlled = nullptr;
        f.device.crc = STRING_HASHCODE("object/intangible/pet/nhelper_droid.iff");
        check(HelperDroidCleanup::isHelperDevice(&f.device)); // Broken helper PCD can still be cleaned up.
        check(!HelperDroidCleanup::isHelperDevice(nullptr) && !HelperDroidCleanup::isHelperDevice(&f.datapad));
    }
    {
        Fixture f;
        check(destroyObject(&f.device, &f.player));
        check(f.device.dbDeletes == 1 && f.ghost.data.at("HelperDroid/manuallyDeleted") == "1" &&
              f.ghost.saves == 1 && f.player.messages == 1);
        check(events.at(events.size() - 4) == "device-db" && events.at(events.size() - 3) == "opt-out" &&
              events.back() == "message");
    }
    for (int invalid = 0; invalid < 3; ++invalid) {
        Fixture f;
        if (invalid == 0) f.server.loading = true;
        if (invalid == 1) f.pet.storeSucceeds = false;
        if (invalid == 2) f.device.owner = &f.otherPlayer;
        check(!destroyObject(&f.device, &f.player) && f.ghost.data.size() == 1 && f.ghost.saves == 0 && f.player.messages == 0);
    }
    {
        Fixture f;
        SceneObject ordinary;
        check(destroyObject(&ordinary, &f.player) && ordinary.dbDeletes == 1 &&
              f.ghost.data.size() == 1 && f.ghost.saves == 0 && f.player.messages == 1);
    }
    for (bool helper : {false, true}) {
        for (bool owned : {false, true}) {
            Fixture f;
            f.pet.helper = helper;
            if (!owned) f.device.owner = nullptr;
            StorePetTask task(&f.player, &f.pet);
            task.run();
            check(f.pet.stores == (!helper || owned));
        }
    }
    {
        Fixture f;
        f.pet.device = nullptr;
        StorePetTask task(&f.player, &f.pet);
        task.run();
        check(f.pet.stores == 0);
    }
    std::cout << passed << " standalone helper droid cleanup checks passed\n";
}
'''


def main():
    cleanup = (CORE / "src/server/zone/objects/player/HelperDroidCleanup.h").read_text()
    cleanup = cleanup[cleanup.index("class HelperDroidCleanup"):cleanup.rindex("#endif")]
    command = (CORE / "src/server/zone/objects/creature/commands/ServerDestroyObjectCommand.h").read_text()
    deletion = function(command, "bool destroyObject(").replace(
        "CreatureObject* creature) const {", "CreatureObject* creature) {")
    store_source = (CORE / "src/server/zone/objects/intangible/tasks/StorePetTask.cpp").read_text()
    store = function(store_source, "void StorePetTask::run()")
    store = store[:store.index('\tif (pet->containsPendingTask("droid_power"))')]
    store += r'''
        ++pet->stores;
        events.push_back("store");
        if (pet->storeSucceeds) {
            pet->localZone = nullptr;
            pet->parent = nullptr;
            pet->linked = nullptr;
            player->getPlayerObject()->active.clear();
        }
    }
    '''
    source = MOCKS + store + cleanup + deletion + CASES
    with tempfile.TemporaryDirectory(prefix="helper-cleanup-check-", dir=CORE / "bin") as temporary:
        folder = Path(temporary)
        cpp, executable = folder / "check.cpp", folder / "check"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Wno-unused-parameter",
                                  str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
