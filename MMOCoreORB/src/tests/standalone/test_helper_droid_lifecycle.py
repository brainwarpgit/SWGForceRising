#!/usr/bin/env python3
"""Exercise helper provisioning and pet-call guards with standalone C++ mocks.

Extracts the complete production SpawnHelperDroidTask, the addSkill helper
branch, helper interaction methods, and early callObject/spawnObject validation
paths. The remainder of ordinary pet calling is a recording stub. No Core3
components or engine3 headers are built or executed.
Real task scheduling, locking, database persistence, and client behavior still
require Core3/in-game verification by the user.
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
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


MOCKS = r'''
#include <cassert>
#include <functional>
#include <iostream>
#include <map>
#include <string>
#include <vector>
using byte = unsigned char;

class String {
    std::string value;
public:
    String() = default;
    String(const char* text): value(text) {}
    static String valueOf(unsigned long long number) { return std::to_string(number).c_str(); }
    String operator+(const char* suffix) const { return (value + suffix).c_str(); }
    unsigned int hashCode() const { return std::hash<std::string>{}(value); }
    bool operator==(const String& other) const { return value == other.value; }
    bool operator!=(const String& other) const { return value != other.value; }
    bool operator<(const String& other) const { return value < other.value; }
};
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
template<class T> using ManagedWeakReference = Ref<T>;
template<class T, class U> T cast(U* value) { return dynamic_cast<T>(value); }
struct Locker {
    template<class... T> explicit Locker(T...) {}
};
struct Task {
    static int delayed;
    virtual ~Task() = default;
    virtual void run() = 0;
    bool isScheduled() const { return false; }
    void execute() { run(); }
    void schedule(int) { ++delayed; }
};
int Task::delayed = 0;
struct TaskManager {
    int scheduled = 0;
    template<class F> void scheduleTask(F callback, const String&, int) { ++scheduled; }
};
struct Core {
    static TaskManager* getTaskManager() { static TaskManager manager; return &manager; }
};
struct ConfigManager {
    bool enabled = true, autoCall = true;
    static ConfigManager* instance() { static ConfigManager config; return &config; }
    bool isHelperDroidEnabled() const { return enabled; }
    bool isHelperDroidAutoCallOnZoneEnabled() const { return autoCall; }
};
struct CreatureObject;
struct AiAgent;
struct Skill {
    String name;
    Skill(const char* value): name(value) {}
    String getSkillName() const { return name; }
};
struct CreatureTemplate {};
struct CreatureManager;
struct PetControlDevice;
struct ZoneServer;
struct ObjectMenuResponse;
struct StringId {
    String name = "helper_droid";
    void setStringId(const String& value) { name = value; }
    String getFullPath() const { return name; }
};
struct SceneObject {
    virtual ~SceneObject() = default;
    unsigned long long id = 0;
    unsigned long long getObjectID() const { return id; }
    std::vector<SceneObject*> children;
    bool acceptTransfer = true;
    int transfers = 0, broadcasts = 0, destroyed = 0;
    virtual bool isPetControlDevice() const { return false; }
    virtual bool isHelperDroidObject() const { return false; }
    virtual bool isAiAgent() const { return false; }
    bool isMount() const { return false; }
    bool isVehicleObject() const { return false; }
    bool isPobShip() const { return false; }
    bool isLockedByCurrentThread() const { return true; }
    int getContainerObjectsSize() const { return children.size(); }
    Ref<SceneObject*> getContainerObject(int i) { return children.at(i); }
    bool transferObject(SceneObject* object, int) {
        ++transfers;
        if (acceptTransfer) children.push_back(object);
        return acceptTransfer;
    }
    void broadcastObject(SceneObject*, bool) { ++broadcasts; }
    void destroyObjectFromDatabase(bool) { ++destroyed; }
};
struct TangibleObject: SceneObject {};
struct BuildingObject: SceneObject { bool isPrivateStructure() const { return false; } };
struct PlayerObject {
    bool online = true, loading = false, teleporting = false;
    bool privileged = false;
    int age = 0;
    std::vector<AiAgent*> activePets;
    Ref<Ref<SceneObject*>> parent;
    std::map<std::pair<String, String>, String> screenPlayData;
    bool isOnline() const { return online; }
    bool isOnLoadScreen() const { return loading; }
    bool isTeleporting() const { return teleporting; }
    int getCharacterAgeInDays() const { return age; }
    int getActivePetsSize() const { return activePets.size(); }
    AiAgent* getActivePet(int index) { return activePets.at(index); }
    bool isPrivileged() const { return privileged; }
    String getScreenPlayData(const String& screenplay, const String& key) const {
        auto found = screenPlayData.find({screenplay, key});
        return found == screenPlayData.end() ? String("") : found->second;
    }
    void setScreenPlayData(const String& screenplay, const String& key, const String& value) {
        screenPlayData[{screenplay, key}] = value;
    }
    void deleteScreenPlayData(const String& screenplay, const String& key) {
        screenPlayData.erase({screenplay, key});
    }
    void createHelperDroid();
    void notifySceneHelper(bool ground = true);
};
struct Zone {
    bool space = false;
    String name = "tatooine";
    CreatureManager* manager = nullptr;
    bool isSpaceZone() const { return space; }
    String getZoneName() const { return name; }
    CreatureManager* getCreatureManager() { return manager; }
};
struct CreatureObject: TangibleObject {
    ZoneServer* server = nullptr;
    Zone* zone = nullptr;
    PlayerObject* ghost = nullptr;
    SceneObject* datapad = nullptr;
    bool dead = false;
    std::vector<String> messages;
    ZoneServer* getZoneServer() { return server; }
    Zone* getZone() { return zone; }
    PlayerObject* getPlayerObject() { return ghost; }
    SceneObject* getSlottedObject(const String&) { return datapad; }
    bool isDead() const { return dead; }
    Task* getPendingTask(const String&) const { return nullptr; }
    Ref<SceneObject*> getParent() { return nullptr; }
    SceneObject* getRootParent() { return nullptr; }
    void sendSystemMessage(const String& message) { messages.push_back(message); }
    bool hasSkill(const String&) const { return true; }
    bool isPlayerCreature() const { return true; }
    CreatureObject* asCreatureObject() { return this; }
    void trainHelper(Skill* skill);
};
struct AiAgent: CreatureObject { bool isAiAgent() const override { return true; } };
struct HelperDroidObject: AiAgent {
    int templateLoads = 0, childCreations = 0;
    PetControlDevice* device = nullptr;
    CreatureObject* owner = nullptr;
    StringId name;
    bool isHelperDroidObject() const override { return true; }
    void loadTemplateData(CreatureTemplate*) { ++templateLoads; }
    void createChildObjects() { ++childCreations; }
    void setControlDevice(PetControlDevice* value) { device = value; }
    StringId* getObjectName() { return &name; }
    Ref<CreatureObject*> getLinkedCreature() { return owner; }
    AiAgent* asAiAgent() { return this; }
    void onCall();
    void notifyHelperDroidSkillTrained(CreatureObject*, const String&);
    int handleObjectMenuSelect(CreatureObject*, byte);
    void fillObjectMenuResponse(ObjectMenuResponse*, CreatureObject*);
};
struct ObjectMenuResponse {
    std::vector<int> choices;
    void addRadialMenuItem(int id, int, const String&) { choices.push_back(id); }
    void addRadialMenuItemToRadialID(int, int id, int, const String&) { choices.push_back(id); }
};
struct SceneObjectImplementation {
    static int stores;
    static int handleObjectMenuSelect(CreatureObject*, byte id) {
        assert(id == 59);
        ++stores;
        return 0;
    }
};
int SceneObjectImplementation::stores = 0;
struct LuaFunction {
    int calls = 0;
    template<class T> LuaFunction& operator<<(T) { return *this; }
    void callFunction() { ++calls; }
};
struct Lua {
    LuaFunction function;
    LuaFunction* createFunction(const String&, const String&, int) { return &function; }
};
struct DirectorManager {
    Lua lua;
    std::map<String, unsigned long long> sharedMemory;
    int sharedWrites = 0;
    static DirectorManager* instance() { static DirectorManager director; return &director; }
    Lua* getLuaInstance() { return &lua; }
    void setSharedMemoryValue(const String& key, unsigned long long value) {
        sharedMemory[key] = value;
        ++sharedWrites;
    }
};
struct PetManager { enum { CREATUREPET = 0, DROIDPET = 2, HELPERDROIDPET = 3 }; };
struct FrsManager {
    bool isFrsEnabled() const { return false; }
    bool isPlayerInEnclave(CreatureObject*) const { return false; }
};
struct PetControlDevice: SceneObject {
    int petType = PetManager::DROIDPET;
    int callsPastGuard = 0, spawnsPastGuard = 0;
    bool owned = true;
    Ref<TangibleObject*> controlledObject;
    ZoneServer* server = nullptr;
    bool isPetControlDevice() const override { return true; }
    bool isASubChildOf(CreatureObject*) const { return owned; }
    ZoneServer* getZoneServer() { return server; }
    int getPetType() const { return petType; }
    TangibleObject* getControlledObject() { return controlledObject.get(); }
    void setPetType(int value) { petType = value; }
    void setControlledObject(TangibleObject* value) { controlledObject = value; }
    void setObjectName(const StringId&, bool) {}
    void setMaxVitality(int) {}
    void setVitality(int) {}
    void callObject(CreatureObject*, bool = false);
    void spawnObject(CreatureObject*);
};
struct ZoneServer {
    int creations = 0;
    PetControlDevice* nextDevice = nullptr;
    FrsManager frs;
    std::vector<Zone*> zones;
    FrsManager* getFrsManager() { return &frs; }
    Ref<SceneObject*> createObject(unsigned int, int) { ++creations; return nextDevice; }
    int getZoneCount() const { return zones.size(); }
    Zone* getZone(int index) { return zones.at(index); }
    Zone* getZone(const String& name) {
        for (auto zone : zones) if (zone->getZoneName() == name) return zone;
        return nullptr;
    }
};
struct CreatureManager {
    int creations = 0;
    CreatureObject* nextCreature = nullptr;
    Ref<CreatureObject*> createCreature(unsigned int, bool, unsigned int) {
        ++creations;
        return nextCreature;
    }
};
struct CreatureTemplateManager {
    CreatureTemplate data;
    bool available = true;
    static CreatureTemplateManager* instance() { static CreatureTemplateManager manager; return &manager; }
    CreatureTemplate* getTemplate(unsigned int) { return available ? &data : nullptr; }
};
struct Fixture {
    ZoneServer server;
    CreatureManager manager;
    Zone zone;
    PlayerObject ghost;
    CreatureObject player;
    SceneObject datapad;
    HelperDroidObject droid, existingDroid;
    PetControlDevice device, existingDevice;
    AiAgent ordinaryPet;
    Fixture() {
        *ConfigManager::instance() = ConfigManager();
        CreatureTemplateManager::instance()->available = true;
        DirectorManager::instance()->lua.function.calls = 0;
        DirectorManager::instance()->sharedMemory = {{"17:HelperDroidID:", 88}};
        DirectorManager::instance()->sharedWrites = 0;
        SceneObjectImplementation::stores = 0;
        Core::getTaskManager()->scheduled = 0;
        Task::delayed = 0;
        player.server = &server;
        player.id = 17;
        droid.id = 99;
        existingDroid.id = 88;
        player.zone = &zone;
        player.ghost = &ghost;
        ghost.parent = Ref<SceneObject*>(&player);
        player.datapad = &datapad;
        zone.manager = &manager;
        server.zones.push_back(&zone);
        server.nextDevice = &device;
        manager.nextCreature = &droid;
        device.server = existingDevice.server = &server;
        existingDevice.petType = PetManager::HELPERDROIDPET;
        existingDevice.controlledObject = &existingDroid;
    }
    void existing() { datapad.children.push_back(&existingDevice); }
};
'''


TESTS = r'''
int main() {
    int passed = 0;
    auto check = [&](bool success) { assert(success); ++passed; };
    for (bool scene : {false, true}) {
        for (bool automatic : {false, true}) {
            Fixture f;
            ConfigManager::instance()->autoCall = automatic;
            SpawnHelperDroidTask task(&f.player, scene);
            task.run();
            check(f.server.creations == 1 && f.manager.creations == 1 &&
                  f.datapad.children.size() == 1 && f.datapad.broadcasts == 1 &&
                  f.device.getPetType() == PetManager::HELPERDROIDPET &&
                  f.device.getControlledObject() == &f.droid && f.droid.device == &f.device &&
                  f.droid.templateLoads == 1 && f.droid.childCreations == 1 &&
                  f.device.callsPastGuard == 1);
            // After initial delivery the device is existing/stored: later
            // scene events may recall it only when scene auto-calls are on.
            task.run();
            check(f.server.creations == 1 && f.datapad.children.size() == 1 &&
                  f.device.callsPastGuard == 1 + (!scene || automatic));
        }
    }
    for (bool automatic : {false, true}) {
        Fixture f;
        f.existing();
        ConfigManager::instance()->autoCall = automatic;
        SpawnHelperDroidTask(&f.player, true).run();
        check(f.server.creations == 0 && f.existingDevice.callsPastGuard == automatic &&
              f.datapad.broadcasts == 0);
    }
    // The default constructor mode is the separate novice-training trigger.
    {
        Fixture f;
        f.existing();
        ConfigManager::instance()->autoCall = false;
        SpawnHelperDroidTask(&f.player).run();
        check(f.server.creations == 0 && f.existingDevice.callsPastGuard == 1);
    }
    // Run the actual addSkill helper branch for every eligible novice. The
    // recorder leaves its follow-up notification queued just as the server does.
    for (const char* novice : {"combat_brawler_novice", "combat_marksman_novice",
            "outdoors_scout_novice", "science_medic_novice", "crafting_artisan_novice",
            "social_entertainer_novice"}) {
        for (bool existing : {false, true}) {
            Fixture f;
            if (existing) f.existing();
            ConfigManager::instance()->autoCall = false;
            Skill skill(novice);
            f.player.trainHelper(&skill);
            check(f.server.creations == !existing &&
                  f.device.callsPastGuard == !existing &&
                  f.existingDevice.callsPastGuard == existing &&
                  Core::getTaskManager()->scheduled == 1);
        }
        {
            Fixture f;
            ConfigManager::instance()->enabled = false;
            Skill skill(novice);
            f.player.trainHelper(&skill);
            check(f.server.creations == 0 && Core::getTaskManager()->scheduled == 0);
        }
    }
    {
        Fixture f;
        ConfigManager::instance()->autoCall = false;
        Skill skill("combat_brawler_unarmed_01");
        f.player.trainHelper(&skill);
        check(f.server.creations == 0 && Core::getTaskManager()->scheduled == 0);
    }
    {
        Fixture f;
        f.ghost.age = 1;
        Skill skill("combat_brawler_novice");
        f.player.trainHelper(&skill);
        check(f.server.creations == 0 && Core::getTaskManager()->scheduled == 0);
    }
    {
        Fixture f;
        ConfigManager::instance()->autoCall = false;
        f.ghost.activePets.push_back(&f.existingDroid);
        Skill skill("combat_brawler_novice");
        f.player.trainHelper(&skill);
        check(f.server.creations == 0 && Core::getTaskManager()->scheduled == 0 &&
              DirectorManager::instance()->lua.function.calls == 1);
    }
    // Ordinary login repairs a missing helper silently, regardless of account
    // age, staff status or loading state, and never recalls an existing helper.
    for (bool automatic : {false, true}) {
        for (bool existing : {false, true}) {
            Fixture f;
            if (existing) f.existing();
            f.ghost.age = 90;
            f.ghost.privileged = true;
            f.ghost.loading = f.ghost.teleporting = true;
            ConfigManager::instance()->autoCall = automatic;
            SpawnHelperDroidTask(&f.player, false, true).run();
            check(f.server.creations == !existing && f.device.callsPastGuard == 0 &&
                  f.existingDevice.callsPastGuard == 0 &&
                  f.ghost.getScreenPlayData("HelperDroid", "loginProvisioned") == (existing ? "" : "1"));
            auto director = DirectorManager::instance();
            check(director->sharedWrites == !existing &&
                  director->sharedMemory["17:HelperDroidID:"] == (existing ? 88 : 99) &&
                  director->lua.function.calls == 0);
        }
    }
    for (bool automatic : {false, true}) {
        Fixture f;
        ConfigManager::instance()->autoCall = automatic;
        SpawnHelperDroidTask(&f.player, false, true).run();
        f.ghost.notifySceneHelper();
        check(f.device.callsPastGuard == 0 && Task::delayed == 0 &&
              f.ghost.getScreenPlayData("HelperDroid", "loginProvisioned") == "");
        f.ghost.notifySceneHelper();
        check(Task::delayed == 1); // Only the login's scene callback is suppressed.
    }
    {
        Fixture f;
        f.zone.space = true;
        f.zone.manager = nullptr;
        Zone ground;
        ground.manager = &f.manager;
        f.server.zones.push_back(&ground);
        SpawnHelperDroidTask(&f.player, false, true).run();
        check(f.server.creations == 1 && f.device.callsPastGuard == 0 &&
              f.ghost.getScreenPlayData("HelperDroid", "loginProvisioned") == "1");
        check(DirectorManager::instance()->sharedWrites == 1 &&
              DirectorManager::instance()->sharedMemory["17:HelperDroidID:"] == 99 &&
              DirectorManager::instance()->lua.function.calls == 0);
        f.ghost.notifySceneHelper(false);
        check(Task::delayed == 0 && f.ghost.getScreenPlayData("HelperDroid", "loginProvisioned") == "");
    }
    {
        Fixture f;
        f.zone.name = "tutorial";
        SpawnHelperDroidTask(&f.player, false, true).run();
        check(f.server.creations == 0 && f.ghost.getScreenPlayData("HelperDroid", "loginProvisioned") == "");
    }
    {
        Fixture f;
        ConfigManager::instance()->enabled = false;
        SpawnHelperDroidTask(&f.player, false, true).run();
        check(f.server.creations == 0 && f.device.callsPastGuard == 0);
    }
    for (int mode = 0; mode < 3; ++mode) {
        for (bool existing : {false, true}) {
            Fixture f;
            if (existing) f.existing();
            f.ghost.setScreenPlayData("HelperDroid", "manuallyDeleted", "1");
            SpawnHelperDroidTask(&f.player, mode == 1, mode == 2).run();
            check(f.server.creations == 0 && f.device.callsPastGuard == 0 &&
                  f.existingDevice.callsPastGuard == 0 &&
                  f.ghost.getScreenPlayData("HelperDroid", "manuallyDeleted") == "1" &&
                  DirectorManager::instance()->sharedWrites == 0 &&
                  DirectorManager::instance()->sharedMemory["17:HelperDroidID:"] == 88);
        }
    }
    {
        Fixture f;
        f.ghost.setScreenPlayData("HelperDroid", "manuallyDeleted", "1");
        f.ghost.activePets.push_back(&f.existingDroid);
        Skill skill("combat_brawler_novice");
        f.player.trainHelper(&skill);
        check(Core::getTaskManager()->scheduled == 0 && f.server.creations == 0 &&
              DirectorManager::instance()->lua.function.calls == 0);
    }
    {
        Fixture f;
        f.datapad.acceptTransfer = false;
        SpawnHelperDroidTask(&f.player, false, true).run();
        check(f.device.destroyed == 1 && f.droid.destroyed == 1 &&
              f.ghost.getScreenPlayData("HelperDroid", "loginProvisioned") == "" &&
              DirectorManager::instance()->sharedWrites == 0 &&
              DirectorManager::instance()->sharedMemory["17:HelperDroidID:"] == 88);
    }
    // Queued tasks re-evaluate state and settings when they run.
    for (int invalid = 0; invalid < 9; ++invalid) {
        for (bool existing : {false, true}) {
            Fixture f;
            if (existing) f.existing();
            SpawnHelperDroidTask task(&f.player, true);
            if (invalid == 0) ConfigManager::instance()->enabled = false;
            if (invalid == 1) f.ghost.online = false;
            if (invalid == 2) f.ghost.loading = true;
            if (invalid == 3) f.ghost.teleporting = true;
            if (invalid == 4) f.zone.space = true;
            if (invalid == 5) f.zone.name = "tutorial";
            if (invalid == 6) f.player.zone = nullptr;
            if (invalid == 7) f.player.ghost = nullptr;
            if (invalid == 8) f.player.server = nullptr;
            task.run();
            check(f.server.creations == 0 && f.device.callsPastGuard == 0 &&
                  f.existingDevice.callsPastGuard == 0 && f.datapad.broadcasts == 0);
        }
    }
    {
        Fixture f;
        SpawnHelperDroidTask task(&f.player, true);
        ConfigManager::instance()->autoCall = false;
        task.run();
        check(f.server.creations == 1 && f.device.callsPastGuard == 1);
        task.run();
        check(f.server.creations == 1 && f.device.callsPastGuard == 1);
    }
    {
        Fixture f;
        ConfigManager::instance()->enabled = false;
        SpawnHelperDroidTask(&f.player).run();
        check(f.server.creations == 0); // Training cannot bypass the master switch.
    }
    {
        Fixture f;
        SpawnHelperDroidTask(nullptr).run();
        check(f.server.creations == 0);
    }
    for (int missing = 0; missing < 3; ++missing) {
        Fixture f;
        if (missing == 0) f.player.datapad = nullptr;
        if (missing == 1) f.zone.manager = nullptr;
        if (missing == 2) CreatureTemplateManager::instance()->available = false;
        SpawnHelperDroidTask(&f.player, true).run();
        check(f.server.creations == 0 && f.datapad.broadcasts == 0);
    }
    {
        Fixture f;
        f.server.nextDevice = nullptr;
        SpawnHelperDroidTask(&f.player, true).run();
        check(f.server.creations == 1 && f.manager.creations == 0 && f.datapad.broadcasts == 0);
    }
    {
        Fixture f;
        f.manager.nextCreature = nullptr;
        SpawnHelperDroidTask(&f.player, true).run();
        check(f.device.destroyed == 1 && f.datapad.broadcasts == 0 && f.device.callsPastGuard == 0);
    }
    {
        Fixture f;
        f.manager.nextCreature = &f.ordinaryPet;
        SpawnHelperDroidTask(&f.player, true).run();
        check(f.device.destroyed == 1 && f.ordinaryPet.destroyed == 1 && f.datapad.broadcasts == 0);
    }
    for (bool automatic : {false, true}) {
        Fixture f;
        f.datapad.acceptTransfer = false;
        ConfigManager::instance()->autoCall = automatic;
        SpawnHelperDroidTask(&f.player, true).run();
        check(f.device.destroyed == 1 && f.droid.destroyed == 1 &&
              f.datapad.children.empty() && f.datapad.broadcasts == 0 && f.device.callsPastGuard == 0);
    }
    // Execute the actual early call/spawn paths; only subsequent pet mechanics
    // are replaced by the recording counters checked here.
    for (bool enabled : {false, true}) {
        for (bool automatic : {false, true}) {
            for (int kind = 0; kind < 3; ++kind) {
                Fixture f;
                ConfigManager::instance()->enabled = enabled;
                ConfigManager::instance()->autoCall = automatic;
                f.device.petType = kind == 0 ? PetManager::HELPERDROIDPET : PetManager::DROIDPET;
                f.device.controlledObject = kind == 1 ? &f.droid : &f.ordinaryPet;
                f.device.callObject(&f.player);
                f.device.spawnObject(&f.player);
                const bool allowed = enabled || kind == 2;
                check(f.device.callsPastGuard == allowed && f.device.spawnsPastGuard == allowed &&
                      f.player.messages.size() == static_cast<unsigned int>(!allowed));
            }
        }
    }
    {
        Fixture f;
        f.device.petType = PetManager::HELPERDROIDPET;
        f.device.controlledObject = &f.droid;
        f.device.callObject(&f.player);
        ConfigManager::instance()->enabled = false;
        f.device.spawnObject(&f.player);
        check(f.device.callsPastGuard == 1 && f.device.spawnsPastGuard == 0);
    }
    for (bool enabled : {false, true}) {
        Fixture f;
        ConfigManager::instance()->enabled = enabled;
        f.droid.owner = &f.player;
        f.droid.onCall();
        f.droid.notifyHelperDroidSkillTrained(&f.player, "combat_brawler_novice");
        check(DirectorManager::instance()->lua.function.calls == 2 * enabled);
        for (byte id : {111, 182, 170}) f.droid.handleObjectMenuSelect(&f.player, id);
        check(DirectorManager::instance()->lua.function.calls == 5 * enabled &&
              f.player.messages.size() == 3 * static_cast<unsigned int>(!enabled));
        f.droid.handleObjectMenuSelect(&f.player, 59);
        check(SceneObjectImplementation::stores == 1);
        ObjectMenuResponse menu;
        f.droid.fillObjectMenuResponse(&menu, &f.player);
        check(enabled ? menu.choices.size() > 2 : menu.choices == std::vector<int>({132, 59}));
    }
    std::cout << "helper droid lifecycle: " << passed << " checks passed\n";
}
'''


def main():
    task_source = (CORE / "src/server/zone/objects/player/events/SpawnHelperDroidTask.h").read_text()
    task = task_source[task_source.index("class SpawnHelperDroidTask"):task_source.rindex("#endif")]
    pet_source = (CORE / "src/server/zone/objects/intangible/PetControlDeviceImplementation.cpp").read_text()
    call = function(pet_source, "void PetControlDeviceImplementation::callObject(")
    call = call[:call.index("\tManagedReference<AiAgent*> pet =")]
    call += "\n\t++callsPastGuard;\n}"
    spawn = function(pet_source, "void PetControlDeviceImplementation::spawnObject(")
    spawn = spawn[:spawn.index("\tManagedReference<TradeSession*> tradeContainer =")]
    spawn += "\n\t++spawnsPastGuard;\n}"
    call = call.replace("PetControlDeviceImplementation::", "PetControlDevice::")
    spawn = spawn.replace("PetControlDeviceImplementation::", "PetControlDevice::")
    helper_source = (CORE / "src/server/zone/objects/creature/ai/HelperDroidObjectImplementation.cpp").read_text()
    helper = "\n".join(function(helper_source, signature) for signature in (
        "void HelperDroidObjectImplementation::onCall(",
        "void HelperDroidObjectImplementation::notifyHelperDroidSkillTrained(",
        "int HelperDroidObjectImplementation::handleObjectMenuSelect(",
        "void HelperDroidObjectImplementation::fillObjectMenuResponse(",
    ))
    helper = helper.replace("HelperDroidObjectImplementation::", "HelperDroidObject::")
    creature_source = (CORE / "src/server/zone/objects/creature/CreatureObjectImplementation.cpp").read_text()
    add_skill = function(creature_source, "void CreatureObjectImplementation::addSkill(")
    training = function(add_skill, "if (isPlayerCreature())")
    training = "void CreatureObject::trainHelper(Skill* skill) {\n" + training + "\n}\n"
    player_source = (CORE / "src/server/zone/objects/player/PlayerObjectImplementation.cpp").read_text()
    scene = function(player_source, "void PlayerObjectImplementation::createHelperDroid(")
    scene = scene.replace("PlayerObjectImplementation::", "PlayerObject::")
    scene_ready = function(player_source, "void PlayerObjectImplementation::notifySceneReady(")
    flag = scene_ready[scene_ready.index("\tconst bool helperProvisionedOnLogin"):scene_ready.index("\n\tteleporting = false")]
    call_start = scene_ready.index("\t\tif (!helperProvisionedOnLogin)")
    call_end = scene_ready.index("createHelperDroid();", call_start) + len("createHelperDroid();")
    scene_call = scene_ready[call_start:call_end]
    # Keep the actual flag consumption/call guard while omitting unrelated
    # weather/chat/client work and supplying its enclosing ground-scene branch.
    notification = "void PlayerObject::notifySceneHelper(bool ground) {\n" + flag
    notification += "\nif (ground) {\n" + scene_call + "\n}\n}\n"
    harness = MOCKS + call + spawn + helper + task + training + scene + notification + TESTS
    with tempfile.TemporaryDirectory(prefix="helper-droid-test-", dir=CORE / "bin") as directory:
        path = Path(directory)
        source = path / "test.cpp"
        executable = path / "test"
        source.write_text(harness)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Wno-unused-parameter",
                                  "-Wno-unused-variable", str(source), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
