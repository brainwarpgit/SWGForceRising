#!/usr/bin/env python3
"""Exercise extracted revocation permission, command, callback, and confirm code.

Uses standalone mocks, including a simulated permission change during cross-lock.
No Core3/engine3 build or access is needed. This does not prove real lock behavior,
client rendering, real administrative grants, gameplay side effects, or persistence.
The request method's real guards and presentation block are extracted separately;
its intervening skill-list/point-summary/window-registration integration is not run.
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
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


MOCKS = r'''
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <functional>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
using uint32 = uint32_t;
using uint64 = uint64_t;
class String {
    std::string value;
public:
    String() = default;
    String(const char* v): value(v) {}
    String(std::string v): value(v) {}
    bool isEmpty() const { return value.empty(); }
    int length() const { return static_cast<int>(value.size()); }
    char charAt(int i) const { return value.at(i); }
    const char* toCharArray() const { return value.c_str(); }
    const std::string& str() const { return value; }
    static String valueOf(int v) { return std::to_string(v); }
    uint32 hashCode() const { return static_cast<uint32>(std::hash<std::string>{}(value)); }
    String trim() const {
        auto first = value.find_first_not_of(" \t\n");
        return first == std::string::npos ? String() : String(value.substr(first, value.find_last_not_of(" \t\n") - first + 1));
    }
    String toLowerCase() const {
        std::string lower = value;
        std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char c) { return std::tolower(c); });
        return lower;
    }
    friend bool operator==(const String& a, const String& b) { return a.value == b.value; }
    friend bool operator!=(const String& a, const String& b) { return !(a == b); }
    friend String operator+(const String& a, const String& b) { return a.value + b.value; }
};
template<class T> class Vector: public std::vector<T> {
public:
    using std::vector<T>::vector;
    int size() const { return static_cast<int>(std::vector<T>::size()); }
    const T& get(int i) const { return this->at(i); }
    void add(const T& item) { this->push_back(item); }
};
struct UnicodeString: String { using String::String; String toString() const { return *this; } };
struct Integer { static int valueOf(const String& v) { return std::stoi(v.str()); } };
struct StringIdManager {
    std::unordered_map<uint32, UnicodeString> labels;
    static StringIdManager* instance() { static StringIdManager instance; return &instance; }
    UnicodeString getStringId(uint32 id) { return labels[id]; }
};
template<class T> struct ManagedReference {
    T value;
    ManagedReference(T v = nullptr): value(v) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
};
struct CreatureObject;
struct SceneObject {
    bool player = false;
    virtual ~SceneObject() = default;
    bool isPlayerCreature() const { return player; }
    virtual CreatureObject* asCreatureObject() { return nullptr; }
};
struct PlayerObject {
    bool online = true, god = true, ability = true;
    bool isOnline() const { return online; }
    bool hasGodMode() const { return god; }
    bool hasAbility(const String& name) const { assert(name == "revokeskill"); return ability; }
};
struct ZoneServer;
struct ZoneProcessServer {
    ZoneServer* zone;
    ZoneServer* getZoneServer() { return zone; }
};
struct QueueCommand {
    enum { SUCCESS, GENERALERROR, INVALIDSTATE, INVALIDLOCOMOTION, INSUFFICIENTPERMISSION, INVALIDTARGET };
    ZoneProcessServer* server;
    bool state = true, motion = true;
    QueueCommand(const String&, ZoneProcessServer* server): server(server) {}
    void setCharacterAbility(const String& name) { assert(name == "admin"); }
    bool checkStateMask(CreatureObject*) const { return state; }
    bool checkInvalidLocomotions(CreatureObject*) const { return motion; }
};
struct ObjectController {
    QueueCommand command{"revokeskill", nullptr};
    bool available = true;
    const QueueCommand* getQueueCommand(const String& name) { assert(name == "revokeskill"); return available ? &command : nullptr; }
};
struct ZoneServer {
    std::unordered_map<uint64, SceneObject*> objects;
    ObjectController controller;
    bool hasController = true;
    ObjectController* getObjectController() { return hasController ? &controller : nullptr; }
    ManagedReference<SceneObject*> getObject(uint64 id) { return objects.count(id) ? objects.at(id) : nullptr; }
};
struct CreatureObject: SceneObject {
    PlayerObject ghost;
    bool hasGhost = true;
    ZoneServer* zone = nullptr;
    uint64 id = 0, selectedTarget = 0;
    int lockDepth = 1;
    String name;
    Vector<String> messages;
    CreatureObject() { player = true; }
    CreatureObject* asCreatureObject() override { return this; }
    PlayerObject* getPlayerObject() { return hasGhost ? &ghost : nullptr; }
    ZoneServer* getZoneServer() { return zone; }
    uint64 getObjectID() const { return id; }
    const String& getFirstName() const { return name; }
    void sendSystemMessage(const String& message) { messages.add(message); }
};
bool losePermissionOnCrossLock = false;
struct Locker {
    CreatureObject* target;
    Locker(CreatureObject* target, CreatureObject* actor): target(target) {
        assert(actor->lockDepth > 0); ++target->lockDepth;
        if (losePermissionOnCrossLock) { actor->ghost.god = false; losePermissionOnCrossLock = false; }
    }
    ~Locker() { --target->lockDepth; }
};
struct SuiWindowType { enum { REVOKE_SKILL_SELECT = 1047, REVOKE_SKILL_CONFIRM = 1048 }; };
struct SuiCallback;
struct SuiBox {
    bool list = true;
    int type = SuiWindowType::REVOKE_SKILL_SELECT;
    Vector<String> rows;
    SuiCallback* callback = nullptr;
    bool isListBox() const { return list; }
    int getWindowType() const { return type; }
    void addMenuItem(const String& row) { rows.add(row); }
    void setCallback(SuiCallback* cb) { callback = cb; }
};
struct SuiCallback {
    ZoneServer* server;
    explicit SuiCallback(ZoneServer* server): server(server) {}
    virtual ~SuiCallback() = default;
    virtual void run(CreatureObject*, SuiBox*, uint32, Vector<UnicodeString>*) = 0;
};
struct SkillManager {
    static SkillManager* active;
    static SkillManager* instance() { return active; }
    struct Request { CreatureObject* actor; CreatureObject* target; String selection; };
    Vector<Request> requests;
    Vector<String> plan, removed;
    CreatureObject* plannedTarget = nullptr;
    CreatureObject* removedTarget = nullptr;
    String failSkill;
    bool buildOK = true;
    int buildCalls = 0;
    bool canRevokeSkills(CreatureObject*) const;
    bool validateSkillRevocation(CreatureObject*, CreatureObject*);
    void requestSkillRevocation(CreatureObject*, CreatureObject*, const String&);
    void confirmSkillRevocation(CreatureObject*, CreatureObject*, const String&, const Vector<String>&);
    bool buildSurrenderSkillPlan(CreatureObject* target, const String&, Vector<String>& result, String& error, bool allowPilot) {
        assert(target->lockDepth > 1 && allowPilot); ++buildCalls; plannedTarget = target;
        result = plan; error = "Plan unavailable."; return buildOK;
    }
    bool surrenderSkill(const String& name, CreatureObject* target, bool notify, bool frs, bool pilot) {
        assert(target->lockDepth > 1 && notify && frs && pilot);
        if (name == failSkill) return false;
        removedTarget = target; removed.add(name); return true;
    }
};
SkillManager* SkillManager::active = nullptr;
'''

TESTS = r'''
int main() {
    int passed = 0;
    auto check = [&](bool v) { assert(v); ++passed; };
    SkillManager manager;
    CreatureObject actor, target, other;
    SceneObject nonPlayer;
    ZoneServer zone, differentZone;
    ZoneProcessServer process{&zone};
    RevokeSkillCommand command("revokeskill", &process);
    const Vector<String> skills = {"master", "novice"};
    auto reset = [&] {
        manager = SkillManager(); manager.plan = skills; SkillManager::active = &manager;
        actor = CreatureObject(); actor.id = 1; actor.name = "Admin"; actor.zone = &zone;
        target = CreatureObject(); target.id = 2; target.name = "Player"; target.zone = &zone;
        other = CreatureObject(); other.id = 3; other.name = "Other"; other.zone = &zone;
        zone = ZoneServer(); zone.objects = {{1, &actor}, {2, &target}, {3, &other}, {4, &nonPlayer}};
        command.state = command.motion = true; losePermissionOnCrossLock = false;
    };
    reset();
    check(manager.canRevokeSkills(&actor) && !manager.canRevokeSkills(nullptr));
    for (int bad = 0; bad < 5; ++bad) {
        reset();
        if (bad == 0) actor.player = false;
        if (bad == 1) actor.hasGhost = false;
        if (bad == 2) actor.ghost.online = false;
        if (bad == 3) actor.ghost.god = false;
        if (bad == 4) actor.ghost.ability = false;
        check(command.doQueueCommand(&actor, 2, "all") == QueueCommand::INSUFFICIENTPERMISSION && manager.requests.empty());
    }
    reset();
    check(command.doQueueCommand(&actor, 0, "  ") == QueueCommand::SUCCESS &&
        manager.requests.size() == 1 && manager.requests.get(0).target == &actor && manager.requests.get(0).selection.isEmpty());
    reset();
    check(command.doQueueCommand(&actor, 2, " ALL ") == QueueCommand::SUCCESS &&
        manager.requests.get(0).target == &target && manager.requests.get(0).selection == "all");
    reset();
    check(command.doQueueCommand(&actor, 2, " MASTER ") == QueueCommand::SUCCESS && manager.requests.get(0).selection == "master");
    reset();
    check(command.doQueueCommand(&actor, 999, "all") == QueueCommand::INVALIDTARGET &&
        command.doQueueCommand(&actor, 4, "all") == QueueCommand::INVALIDTARGET && manager.requests.empty());
    reset(); command.state = false;
    check(command.doQueueCommand(&actor, 2, "all") == QueueCommand::INVALIDSTATE && manager.requests.empty());
    reset(); command.motion = false;
    check(command.doQueueCommand(&actor, 2, "all") == QueueCommand::INVALIDLOCOMOTION && manager.requests.empty());
    reset(); losePermissionOnCrossLock = true;
    command.doQueueCommand(&actor, 2, "all");
    check(manager.requests.empty() && !actor.ghost.god && target.lockDepth == 1);
    SuiBox select, confirm; confirm.type = SuiWindowType::REVOKE_SKILL_CONFIRM;
    RevokeSkillSuiCallback choose(&zone, 2, "", skills, false), accept(&zone, 2, "novice", skills, true);
    Vector<UnicodeString> first = {"0"};
    reset();
    for (uint32 event : {1u, 2u, 99u}) accept.run(&actor, &confirm, event, &first);
    check(manager.removed.empty() && manager.requests.empty());
    for (const char* row : {"", "-1", "2", "1x", "+0", "9999999999"}) {
        Vector<UnicodeString> args = {row}; choose.run(&actor, &select, 0, &args);
    }
    choose.run(&actor, &select, 0, nullptr);
    check(manager.requests.empty());
    reset(); actor.selectedTarget = 3;
    choose.run(&actor, &select, 0, &first);
    check(manager.requests.size() == 1 && manager.requests.get(0).target == &target && manager.requests.get(0).selection == "master");
    reset(); actor.ghost.ability = false;
    accept.run(&actor, &confirm, 0, nullptr);
    check(manager.removed.empty() && manager.buildCalls == 0 && actor.messages.size() == 1);
    reset(); losePermissionOnCrossLock = true;
    accept.run(&actor, &confirm, 0, nullptr);
    check(manager.removed.empty() && manager.buildCalls == 0 && target.lockDepth == 1);
    for (int missing = 0; missing < 3; ++missing) {
        reset();
        if (missing == 0) zone.objects.erase(2);
        if (missing == 1) zone.objects[2] = &nonPlayer;
        if (missing == 2) target.ghost.online = false;
        accept.run(&actor, &confirm, 0, nullptr);
        check(manager.removed.empty() && manager.buildCalls == 0 && actor.messages.size() == 1);
    }
    for (int invalid = 0; invalid < 7; ++invalid) {
        reset();
        if (invalid == 0) target.zone = &differentZone;
        if (invalid == 1) target.hasGhost = false;
        if (invalid == 2) actor.zone = nullptr;
        if (invalid == 3) zone.hasController = false;
        if (invalid == 4) zone.controller.available = false;
        if (invalid == 5) zone.controller.command.state = false;
        if (invalid == 6) zone.controller.command.motion = false;
        manager.confirmSkillRevocation(&actor, &target, "novice", skills);
        check(manager.removed.empty() && manager.buildCalls == 0 && target.lockDepth == 1);
    }
    for (const Vector<String>& changed : {Vector<String>{"master"}, Vector<String>{"extra", "master", "novice"}, Vector<String>{"novice", "master"}}) {
        reset(); manager.plan = changed;
        accept.run(&actor, &confirm, 0, nullptr);
        check(manager.removed.empty() && manager.requests.size() == 1 && manager.requests.get(0).target == &target);
    }
    reset(); manager.buildOK = false;
    accept.run(&actor, &confirm, 0, nullptr);
    check(manager.removed.empty() && manager.requests.empty() && actor.messages.size() == 1);
    reset(); actor.selectedTarget = 3;
    accept.run(&actor, &confirm, 0, nullptr);
    check(manager.removed == skills && manager.removedTarget == &target && manager.plannedTarget == &target &&
        actor.messages.size() == 1 && target.messages.size() == 1 && other.messages.empty());
    reset(); manager.confirmSkillRevocation(&actor, &actor, "all", skills);
    check(manager.removed == skills && manager.removedTarget == &actor && actor.messages.size() == 1);
    reset(); manager.failSkill = "novice";
    accept.run(&actor, &confirm, 0, nullptr);
    check(manager.removed == Vector<String>{"master"} && actor.messages.size() == 1 && target.messages.size() == 1);
    reset(); manager.failSkill = "master";
    accept.run(&actor, &confirm, 0, nullptr);
    check(manager.removed.empty() && actor.messages.size() == 1 && target.messages.empty());
    reset();
    accept.run(&actor, &select, 0, nullptr); choose.run(&actor, &confirm, 0, &first);
    accept.run(nullptr, &confirm, 0, nullptr); accept.run(&actor, nullptr, 0, nullptr);
    check(manager.removed.empty() && manager.requests.empty());
    reset();
    auto strings = StringIdManager::instance();
    strings->labels = {{String("@skl_n:master").hashCode(), "Zebra Master"}, {String("@skl_n:novice").hashCode(), "Alpha Novice"}};
    SuiBox sortedSelection;
    present(&actor, &target, &sortedSelection, "", skills, false);
    actor.selectedTarget = 3;
    sortedSelection.callback->run(&actor, &sortedSelection, 0, &first);
    check(sortedSelection.rows == Vector<String>({"@skl_n:novice", "@skl_n:master"}) &&
        manager.requests.get(0).selection == "novice" && manager.requests.get(0).target == &target);
    delete sortedSelection.callback;
    reset();
    SuiBox sortedConfirmation; sortedConfirmation.type = SuiWindowType::REVOKE_SKILL_CONFIRM;
    present(&actor, &target, &sortedConfirmation, "novice", skills, true);
    sortedConfirmation.callback->run(&actor, &sortedConfirmation, 0, &first);
    check(sortedConfirmation.rows == Vector<String>({"@skl_n:novice", "@skl_n:master"}) &&
        manager.removed == skills && manager.requests.empty());
    delete sortedConfirmation.callback;
    std::cout << passed << " skill revocation checks passed\n";
}
'''


def main():
    source = (CORE / "src/server/zone/managers/skill/SkillManager.cpp").read_text()
    methods = "\n".join(function(source, signature) for signature in (
        "Vector<String> getSkillsByDisplayName(", "bool SkillManager::canRevokeSkills(",
        "bool SkillManager::validateSkillRevocation(", "void SkillManager::confirmSkillRevocation("))
    request = function(source, "void SkillManager::requestSkillRevocation(")
    # Exercise actual validation after cross-lock; mock only the remaining UI workflow.
    request_entry = request[:request.index("\tauto ghost = actor->getPlayerObject();")]
    request_entry += "requests.add({actor, target, selection});\n}\n"
    presentation = request[request.index("\tconst Vector<String> displayedSkills"):request.index("\tghost->addSuiBox(box);")]
    presentation = "void present(CreatureObject* actor, CreatureObject* target, SuiBox* box, const String& selection, const Vector<String>& skills, bool confirmation) {\n" + presentation + "}\n"
    callback = (CORE / "src/server/zone/objects/player/sui/callbacks/RevokeSkillSuiCallback.h").read_text()
    callback = callback[callback.index("class RevokeSkillSuiCallback"):callback.rindex("#endif")]
    command = (CORE / "src/server/zone/objects/creature/commands/RevokeSkillCommand.h").read_text()
    command = command[command.index("class RevokeSkillCommand"):command.rindex("#endif")]
    with tempfile.TemporaryDirectory(prefix="skill-revocation-", dir=CORE / "bin") as folder:
        cpp, executable = Path(folder) / "check.cpp", Path(folder) / "check"
        cpp.write_text(MOCKS + methods + request_entry + callback + command + presentation + TESTS)
        compiler = shlex.split(os.environ.get("CXX", "g++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", str(cpp), "-o", str(executable)], check=True, timeout=30)
        subprocess.run([str(executable)], check=True, timeout=10)


if __name__ == "__main__":
    main()
