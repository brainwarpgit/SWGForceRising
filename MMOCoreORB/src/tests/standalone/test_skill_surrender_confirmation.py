#!/usr/bin/env python3
"""Exercise the real surrender confirmation/callback with standalone C++ mocks.

No Core3 headers, components, executable, or engine3 sources are compiled. These
checks cover server-side control flow, not client rendering or live skill state.
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
#include <algorithm>
#include <cctype>
#include <functional>
#include <iostream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>
#include <cstdint>
using uint32 = uint32_t;
class String {
    std::string value;
public:
    String() = default;
    String(const char* text): value(text) {}
    String(std::string text): value(text) {}
    bool isEmpty() const { return value.empty(); }
    int length() const { return static_cast<int>(value.size()); }
    char charAt(int index) const { return value.at(index); }
    static String valueOf(int number) { return std::to_string(number); }
    const std::string& str() const { return value; }
    const char* toCharArray() const { return value.c_str(); }
    uint32 hashCode() const { return static_cast<uint32>(std::hash<std::string>{}(value)); }
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
    bool isEmpty() const { return this->empty(); }
    const T& get(int index) const { return this->at(index); }
    void add(const T& item) { this->push_back(item); }
};
class UnicodeString: public String {
public:
    using String::String;
    String toString() const { return *this; }
};
struct StringIdManager {
    std::unordered_map<uint32, UnicodeString> labels;
    int lookups = 0;
    static StringIdManager* instance() { static StringIdManager manager; return &manager; }
    UnicodeString getStringId(uint32 id) { ++lookups; return labels[id]; }
};
struct Integer { static int valueOf(const String& value) { return std::stoi(value.str()); } };
struct PlayerObject { bool online = true; bool isOnline() const { return online; } };
struct CreatureObject;
struct QueueCommand {
    bool validState = true, validMotion = true;
    bool checkStateMask(CreatureObject*) const { return validState; }
    bool checkInvalidLocomotions(CreatureObject*) const { return validMotion; }
};
struct ObjectController {
    QueueCommand command;
    bool hasCommand = true;
    const QueueCommand* getQueueCommand(const String& name) {
        assert(name == "surrenderskill");
        return hasCommand ? &command : nullptr;
    }
};
struct ZoneServer {
    ObjectController controller;
    bool hasController = true;
    ObjectController* getObjectController() { return hasController ? &controller : nullptr; }
};
struct CreatureObject {
    bool player = true;
    PlayerObject ghost;
    ZoneServer zone;
    bool hasGhost = true, hasZone = true;
    int lockDepth = 0;
    Vector<String> messages;
    bool isPlayerCreature() const { return player; }
    PlayerObject* getPlayerObject() { return hasGhost ? &ghost : nullptr; }
    ZoneServer* getZoneServer() { return hasZone ? &zone : nullptr; }
    void sendSystemMessage(const String& message) { messages.add(message); }
};
struct Locker {
    CreatureObject* player;
    explicit Locker(CreatureObject* player): player(player) { ++player->lockDepth; }
    ~Locker() { --player->lockDepth; }
};
struct SuiWindowType { enum { SURRENDER_SKILL_SELECT = 1045, SURRENDER_SKILL_CONFIRM = 1046 }; };
struct SuiCallback;
struct SuiBox {
    bool list = true;
    int type = SuiWindowType::SURRENDER_SKILL_SELECT;
    Vector<String> rows;
    SuiCallback* callback = nullptr;
    bool isListBox() const { return list; }
    int getWindowType() const { return type; }
    void addMenuItem(const String& row) { rows.add(row); }
    void setCallback(SuiCallback* value) { callback = value; }
};
struct SuiCallback {
    explicit SuiCallback(ZoneServer*) {}
    virtual ~SuiCallback() = default;
    virtual void run(CreatureObject*, SuiBox*, uint32, Vector<UnicodeString>*) = 0;
};
class SkillManager {
public:
    static SkillManager* active;
    static SkillManager* instance() { return active; }
    Vector<String> plan, removed, requests;
    bool buildOK = true;
    int buildCalls = 0;
    String failSkill;
    bool buildSurrenderSkillPlan(CreatureObject* player, const String&, Vector<String>& result, String& error) {
        assert(player->lockDepth > 0);
        ++buildCalls;
        result = plan;
        error = "Plan unavailable.";
        return buildOK;
    }
    bool surrenderSkill(const String& name, CreatureObject* player, bool notify) {
        assert(player->lockDepth > 0 && notify);
        if (name == failSkill) return false;
        removed.add(name);
        return true;
    }
    void requestSkillSurrender(CreatureObject*, const String& selection) { requests.add(selection); }
    void confirmSkillSurrender(CreatureObject*, const String&, const Vector<String>&);
};
SkillManager* SkillManager::active = nullptr;
'''

TESTS = r'''
int main() {
    int passed = 0;
    auto check = [&](bool result) { assert(result); ++passed; };
    CreatureObject player;
    SkillManager manager;
    SkillManager::active = &manager;
    Vector<String> skills = {"master", "novice"};
    auto reset = [&] { manager = SkillManager(); manager.plan = skills; player = CreatureObject(); };
    reset();
    SuiBox select, confirm;
    confirm.type = SuiWindowType::SURRENDER_SKILL_CONFIRM;
    SurrenderSkillSuiCallback choose(&player.zone, "", skills, false);
    SurrenderSkillSuiCallback accept(&player.zone, "novice", skills, true);
    Vector<UnicodeString> second = {"1"};
    choose.run(&player, &select, 0, &second);
    check(manager.requests.size() == 1 && manager.requests.get(0) == "novice" && manager.removed.isEmpty());
    reset();
    for (uint32 event : {1u, 2u, 99u}) accept.run(&player, &confirm, event, &second);
    check(manager.removed.isEmpty() && manager.requests.isEmpty());
    for (const char* index : {"", "-1", "2", "1a", "+1", "1.0", "9999999999", " 1"}) {
        Vector<UnicodeString> args = {index};
        choose.run(&player, &select, 0, &args);
    }
    check(manager.requests.isEmpty());
    Vector<UnicodeString> empty;
    choose.run(&player, &select, 0, nullptr);
    choose.run(&player, &select, 0, &empty);
    check(manager.requests.isEmpty());
    accept.run(&player, &confirm, 0, nullptr);
    check(manager.removed == skills && player.lockDepth == 0 && player.messages.size() == 1);
    reset();
    Vector<UnicodeString> noRow = {"-1"};
    accept.run(&player, &confirm, 0, &noRow);
    check(manager.removed == skills); // Confirmation applies to every displayed row.
    for (const Vector<String>& changed : {Vector<String>{"master"}, Vector<String>{"extra", "master", "novice"}, Vector<String>{"novice", "master"}}) {
        reset(); manager.plan = changed;
        accept.run(&player, &confirm, 0, nullptr);
        check(manager.removed.isEmpty() && manager.requests.size() == 1 && manager.requests.get(0) == "novice");
    }
    reset(); manager.buildOK = false;
    accept.run(&player, &confirm, 0, nullptr);
    check(manager.removed.isEmpty() && manager.requests.isEmpty() && player.messages.get(0).str().find("No skills were surrendered") != std::string::npos);
    for (int condition = 0; condition < 4; ++condition) {
        reset();
        if (condition == 0) player.player = false;
        if (condition == 1) player.ghost.online = false;
        if (condition == 2) player.hasGhost = false;
        if (condition == 3) player.hasZone = false;
        accept.run(&player, &confirm, 0, nullptr);
        check(manager.removed.isEmpty() && player.lockDepth == 0);
    }
    for (int condition = 0; condition < 4; ++condition) {
        reset();
        if (condition == 0) player.zone.controller.command.validState = false;
        if (condition == 1) player.zone.controller.command.validMotion = false;
        if (condition == 2) player.zone.controller.hasCommand = false;
        if (condition == 3) player.zone.hasController = false;
        accept.run(&player, &confirm, 0, nullptr);
        check(manager.removed.isEmpty() && manager.requests.isEmpty() && manager.buildCalls == 0 &&
            player.lockDepth == 0 && player.messages.size() == 1 &&
            player.messages.get(0).str().find("No skills were surrendered") != std::string::npos);
    }
    reset(); manager.plan = {"master", "middle", "novice"}; manager.failSkill = "middle";
    manager.confirmSkillSurrender(&player, "novice", manager.plan);
    check(manager.removed == Vector<String>{"master"} && player.messages.get(0).str().find("stopped after 1 skills") != std::string::npos);
    reset();
    accept.run(&player, &select, 0, nullptr);
    choose.run(&player, &confirm, 0, &second);
    select.list = false; choose.run(&player, &select, 0, &second);
    accept.run(nullptr, &confirm, 0, nullptr);
    accept.run(&player, nullptr, 0, nullptr);
    check(manager.removed.isEmpty() && manager.requests.isEmpty());
    SkillManager::active = nullptr; accept.run(&player, &confirm, 0, nullptr);
    check(manager.removed.isEmpty());
    manager.confirmSkillSurrender(nullptr, "novice", skills);
    manager.confirmSkillSurrender(&player, "", skills);
    manager.confirmSkillSurrender(&player, "novice", {});
    check(manager.removed.isEmpty());

    auto labels = StringIdManager::instance();
    labels->labels = {{String("@skl_n:master").hashCode(), "Zebra Master"},
        {String("@skl_n:novice").hashCode(), "alpha Novice"},
        {String("@skl_n:tie_b").hashCode(), "Beta"}, {String("@skl_n:tie_a").hashCode(), "bETA"}};
    Vector<String> unsorted = {"master", "tie_b", "missing", "novice", "tie_a"};
    const auto unchanged = unsorted;
    check(getSkillsByDisplayName(unsorted) == Vector<String>({"novice", "tie_a", "tie_b", "missing", "master"}));
    check(unsorted == unchanged && labels->lookups == unsorted.size());
    reset(); SkillManager::active = &manager;
    SuiBox selectionBox;
    present(&player, &selectionBox, "", skills, false);
    check(selectionBox.rows == Vector<String>({"@skl_n:novice", "@skl_n:master"}));
    Vector<UnicodeString> first = {"0"};
    selectionBox.callback->run(&player, &selectionBox, 0, &first);
    check(manager.requests == Vector<String>{"novice"} && manager.removed.isEmpty());
    delete selectionBox.callback;
    reset();
    SuiBox confirmationBox;
    confirmationBox.type = SuiWindowType::SURRENDER_SKILL_CONFIRM;
    present(&player, &confirmationBox, "novice", skills, true);
    check(confirmationBox.rows == Vector<String>({"@skl_n:novice", "@skl_n:master"}));
    confirmationBox.callback->run(&player, &confirmationBox, 0, &first);
    check(manager.removed == skills && manager.requests.isEmpty());
    delete confirmationBox.callback;
    std::cout << passed << " surrender confirmation/callback checks passed\n";
}
'''


def main():
    source = (CORE / "src/server/zone/managers/skill/SkillManager.cpp").read_text()
    confirmation = function(source, "void SkillManager::confirmSkillSurrender(")
    display_sort = function(source, "Vector<String> getSkillsByDisplayName(")
    request = function(source, "void SkillManager::requestSkillSurrender(")
    presentation = request[request.index("\tconst Vector<String> displayedSkills"):request.index("\tghost->addSuiBox(box);")]
    presentation = "void present(CreatureObject* creature, SuiBox* box, const String& selection, const Vector<String>& skills, bool confirmation) {\n" + presentation + "}\n"
    callback_source = (CORE / "src/server/zone/objects/player/sui/callbacks/SurrenderSkillSuiCallback.h").read_text()
    callback = callback_source[callback_source.index("class SurrenderSkillSuiCallback"):callback_source.rindex("#endif")]
    with tempfile.TemporaryDirectory(prefix="surrender-confirm-", dir=CORE / "bin") as folder:
        cpp = Path(folder) / "check.cpp"
        executable = Path(folder) / "check"
        cpp.write_text(MOCKS + display_sort + "\n" + confirmation + "\n" + callback + presentation + TESTS)
        compiler = shlex.split(os.environ.get("CXX", "g++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", str(cpp), "-o", str(executable)], check=True, timeout=30)
        subprocess.run([str(executable)], check=True, timeout=10)


if __name__ == "__main__":
    main()
