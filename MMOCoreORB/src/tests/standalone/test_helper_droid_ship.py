#!/usr/bin/env python3
"""Check helper ship association, delayed insertion and program eligibility.

Compiles extracted production command/task bodies against standard-library
mocks only; does not build or execute Core3 or access engine3. Program effects,
real ship state, locks and persistence remain in-game verification requirements.
"""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]


def body(source, signature):
    start = source.index("{", source.index(signature))
    end, depth = start + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start + 1:end - 1]


MOCKS = r'''
#include <cassert>
#include <cstdint>
#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <unordered_map>
using uint64 = uint64_t;
using uint32 = uint32_t;
struct String : std::string {
    using std::string::string;
    uint32 hashCode() const { return std::hash<std::string>{}(*this); }
};
struct UnicodeString : String {
    using String::String;
    String toString() const { return c_str(); }
};
struct UnicodeTokenizer {
    std::istringstream input;
    UnicodeTokenizer(const UnicodeString& text): input(text) {}
    bool hasMoreTokens() { input >> std::ws; return !input.eof(); }
    uint64 getLongToken() { uint64 result = 0; input >> result; return result; }
};
template<class T> struct Ref {
    T value = nullptr;
    Ref() = default;
    Ref(T v): value(v) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
};
template<class T> using ManagedReference = Ref<T>;
template<class T> using ManagedWeakReference = Ref<T>;
template<class T, class U> T cast(U* value) { return dynamic_cast<T>(value); }
std::function<void()> nextLockHook;
struct Locker {
    template<class... T> Locker(T...) {
        auto callback = nextLockHook;
        nextLockHook = nullptr;
        if (callback) callback();
    }
};
struct ConfigManager {
    bool enabled = true, autoCall = true;
    static ConfigManager* instance() { static ConfigManager value; return &value; }
    bool isHelperDroidEnabled() const { return enabled; }
};
struct PetManager { enum { HELPERDROIDPET = 3 }; };
struct Components { enum { DROID_INTERFACE = 0 }; };
struct PlayerArrangement { enum { RIDER = 0 }; };
struct ShipDroidData {
    enum { NONE = 0, ASTROMECH = 1, FLIGHTCOMPUTER = 2 };
    static uint32 getDroidType(uint32 crc) { return ASTROMECH; }
    static uint32 getShipDroidType(uint32 crc) { return ASTROMECH; }
};
struct ShipObject;
struct CreatureObject;
struct SceneObject {
    virtual ~SceneObject() = default;
    virtual bool isShipObject() const { return false; }
    virtual ShipObject* asShipObject() { return nullptr; }
    virtual bool isPetControlDevice() const { return false; }
    virtual bool isControlDevice() const { return false; }
    virtual bool isHelperDroidObject() const { return false; }
    virtual bool isASubChildOf(CreatureObject*) const { return true; }
    uint64 getObjectID() const { return 2; }
};
struct ZoneServer {
    std::unordered_map<uint64, SceneObject*> objects;
    Ref<SceneObject*> getObject(uint64 id) { return objects[id]; }
};
struct PlayerObject {
    bool hasAbility(const String&) const { return true; }
    bool hasGodMode() const { return false; }
};
struct StringIdChatParameter {
    void setStringId(const char*, const char*) {}
    void setDI(int) {}
};
struct CreatureObject : SceneObject {
    ZoneServer* server = nullptr;
    SceneObject* parent = nullptr;
    PlayerObject ghost;
    int messages = 0;
    ZoneServer* getZoneServer() { return server; }
    PlayerObject* getPlayerObject() { return &ghost; }
    SceneObject* getRootParent() { return parent; }
    bool isPlayerCreature() const { return true; }
    template<class T> void sendSystemMessage(T) { ++messages; }
};
struct IntangibleObject : SceneObject {};
struct DroidObject : SceneObject {
    bool helper = true;
    int inserted = 0;
    bool isHelperDroidObject() const override { return helper; }
    void setMovementCounter(int) {}
    void setDirection(int, int, int, int) {}
    void switchZone(const String&, int, int, int, uint64, bool, int) { ++inserted; }
};
struct PetControlDevice : IntangibleObject {
    DroidObject* controlled = nullptr;
    bool owned = true;
    int petType = PetManager::HELPERDROIDPET;
    bool isPetControlDevice() const override { return true; }
    bool isControlDevice() const override { return true; }
    bool isASubChildOf(CreatureObject*) const override { return owned; }
    DroidObject* getControlledObject() { return controlled; }
    int getPetType() const { return petType; }
    String getRequiredAstromechCert() const { return "cert"; }
    uint32 getServerObjectCRC() const { return 1; }
};
struct Zone { String getZoneName() const { return "space_corellia"; } };
struct ShipObject : SceneObject {
    CreatureObject* owner = nullptr;
    ZoneServer* server = nullptr;
    Zone zone;
    uint64 droidID = 2;
    bool isShipObject() const override { return true; }
    ShipObject* asShipObject() override { return this; }
    Ref<CreatureObject*> getOwner() { return owner; }
    ZoneServer* getZoneServer() { return server; }
    Zone* getLocalZone() { return &zone; }
    bool hasSlotDescriptor(const char*) const { return true; }
    uint64 getShipDroidID() const { return droidID; }
    void setShipDroidID(uint64 id, bool) { droidID = id; }
    bool isComponentInstalled(int) const { return true; }
    bool isComponentFunctional(int) const { return true; }
    String getShipChassisName() const { return "player_z95"; }
    bool isReadyForDroidCommand() const { return true; }
    int timeUntilNextDroidCommand() const { return 0; }
};
struct ShipManager {
    static ShipManager* instance() { static ShipManager value; return &value; }
};
enum { SUCCESS = 0, GENERALERROR = 1, INVALIDSTATE = 2, INVALIDLOCOMOTION = 3 };
bool checkStateMask(CreatureObject*) { return true; }
bool checkInvalidLocomotions(CreatureObject*) { return true; }
'''

CASES = r'''
int main() {
    ZoneServer server;
    CreatureObject player;
    ShipObject ship;
    DroidObject droid;
    PetControlDevice device;
    player.server = &server;
    player.parent = &ship;
    ship.server = &server;
    ship.owner = &player;
    device.controlled = &droid;
    server.objects[1] = &ship;
    server.objects[2] = &device;
    auto config = ConfigManager::instance();
    int tests = 0;
    auto check = [&](bool value) { assert(value); ++tests; };

    config->enabled = false;
    ship.droidID = 0;
    check(associate(&player, 0, "1 2") == GENERALERROR && ship.droidID == 0);
    ship.droidID = 2;
    check(associate(&player, 0, "1 0") == SUCCESS && ship.droidID == 0);
    config->enabled = true;
    check(associate(&player, 0, "1 2") == SUCCESS && ship.droidID == 2);

    config->enabled = false;
    InsertTask task{&ship};
    task.run();
    check(droid.inserted == 0 && ship.droidID == 2);
    check(program(&player, 0, "test") == GENERALERROR && ship.droidID == 2);
    config->enabled = true;
    task.run();
    check(droid.inserted == 1);
    check(program(&player, 0, "test") == SUCCESS);

    // AutoCallOnZone affects the automatic ground helper flow, not a player's
    // explicit ship assignment when the master feature remains enabled.
    config->autoCall = false;
    check(associate(&player, 0, "1 2") == SUCCESS);
    task.run();
    check(droid.inserted == 2);
    check(program(&player, 0, "test") == SUCCESS);

    config->enabled = false;
    device.petType = 1;
    droid.helper = false;
    check(associate(&player, 0, "1 2") == SUCCESS);
    task.run();
    check(droid.inserted == 3);
    check(program(&player, 0, "test") == SUCCESS);

    // Either helper identifier suffices, including legacy mismatched records.
    droid.helper = true;
    check(associate(&player, 0, "1 2") == GENERALERROR);
    task.run();
    check(droid.inserted == 3);
    check(program(&player, 0, "test") == GENERALERROR);
    device.petType = PetManager::HELPERDROIDPET;
    droid.helper = false;
    check(associate(&player, 0, "1 2") == GENERALERROR);
    task.run();
    check(droid.inserted == 3);
    check(program(&player, 0, "test") == GENERALERROR);

    IntangibleObject flightComputer;
    server.objects[2] = &flightComputer;
    check(program(&player, 0, "test") == SUCCESS);

    // Change state after the task captures its references, just as deletion or
    // disassociation could while it waits for the ship and droid locks.
    server.objects[2] = &device;
    config->enabled = true;
    ship.droidID = 2;
    nextLockHook = [&] { ship.droidID = 0; };
    task.run();
    check(droid.inserted == 3);
    ship.droidID = 2;
    nextLockHook = [&] { device.owned = false; };
    task.run();
    check(droid.inserted == 3);
    device.owned = true;
    DroidObject replacement;
    nextLockHook = [&] { device.controlled = &replacement; };
    task.run();
    check(droid.inserted == 3 && replacement.inserted == 0);
    device.controlled = &droid;
    task.run();
    check(droid.inserted == 4);
    std::cout << tests << " standalone helper droid ship checks passed\n";
}
'''


def main():
    commands = CORE / "src/server/zone/objects/creature/commands"
    associate = body((commands / "AssociateDroidControlDeviceWithShipCommand.h").read_text(),
                     "int doQueueCommand(")
    insertion = body((CORE / "src/server/zone/objects/ship/events/InsertAstromechIntoShipTask.h").read_text(),
                     "void run()")
    program = body((commands / "DroidCommand.h").read_text(), "int doQueueCommand(")
    # Only the real preflight through helper validation is compiled; downstream
    # ship combat/program effects are represented by successful eligibility.
    program = program[:program.index("\t\tif (!ship->hasDroidCommand(argsHash))")] + "return SUCCESS;\n"
    source = MOCKS
    signature = "(CreatureObject* creature, const uint64& target, const UnicodeString& arguments)"
    source += "int associate" + signature + " {" + associate + "}\n"
    source += "int program" + signature + " {" + program + "}\n"
    source += "struct InsertTask { ManagedWeakReference<ShipObject*> shipObj; void run() {" + insertion + "}};\n"
    source += CASES
    with tempfile.TemporaryDirectory(prefix="helper-ship-check-", dir=CORE / "bin") as temporary:
        folder = Path(temporary)
        cpp, executable = folder / "check.cpp", folder / "check"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Wno-unused-parameter",
                                  "-Wno-unused-variable", str(cpp), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    main()
