#!/usr/bin/env python3
"""Check actual eligibility/plan adapter code with synthetic skills and Jedi rules.

Only standard-library mocks and the dependency planner are compiled. This does
not build Core3 or access engine3, and does not verify live skill data or Lua.
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
#include <iostream>
#include <string>
#include <vector>
class String {
    std::string value;
public:
    String() = default;
    String(const char* text): value(text) {}
    bool beginsWith(const std::string& prefix) const { return value.rfind(prefix, 0) == 0; }
    bool endsWith(const std::string& suffix) const {
        return value.size() >= suffix.size() && value.compare(value.size() - suffix.size(), suffix.size(), suffix) == 0;
    }
    const char* toCharArray() const { return value.c_str(); }
    bool isEmpty() const { return value.empty(); }
    friend bool operator==(const String& a, const String& b) { return a.value == b.value; }
};
template<class T> class Vector: public std::vector<T> {
public:
    using std::vector<T>::vector;
    int size() const { return static_cast<int>(std::vector<T>::size()); }
    const T& get(int index) const { return this->at(index); }
    void add(const T& item) { this->push_back(item); }
    bool contains(const T& item) const { return std::find(this->begin(), this->end(), item) != this->end(); }
    void removeAll() { this->clear(); }
};
struct Skill {
    String name;
    int points;
    Vector<String> required;
    bool god = false;
    const String& getSkillName() const { return name; }
    int getSkillPointsRequired() const { return points; }
    const Vector<String>* getSkillsRequired() const { return &required; }
    bool isGodOnly() const { return god; }
};
using SkillList = Vector<Skill*>;
struct CreatureObject {
    SkillList owned;
    const SkillList* getSkillList() const { return &owned; }
};
struct JediManager {
    String rejected;
    int forceLimit = 1000;
    std::vector<Vector<String>> checked;
    static JediManager* instance() { static JediManager manager; return &manager; }
    bool canSurrenderSkills(CreatureObject*, const Vector<String>& plan) {
        checked.push_back(plan);
        int forceCount = 0;
        for (const auto& name : plan) {
            if (name == rejected) return false;
            if (name.beginsWith("force_")) ++forceCount;
        }
        return forceCount <= forceLimit;
    }
};
struct SkillManager {
    bool buildSurrenderSkillPlan(CreatureObject*, const String&, Vector<String>&, String&);
};
'''

TESTS = r'''
int main() {
    int passed = 0;
    auto check = [&](bool result) { assert(result); ++passed; };
    std::vector<Skill> zeroCost = {
        {"social_entertainer_novice", 0, {}}, {"social_entertainer_master", 0, {}},
        {"force_sensitive_combat_prowess_novice", 0, {}}, {"force_sensitive_combat_prowess_ranged_accuracy_01", 0, {}},
        {"social_politician_novice", 0, {}}, {"social_politician_master", 0, {}}
    };
    bool allEligible = true;
    for (auto& skill : zeroCost) allEligible &= isPlayerSurrenderableSkill(&skill);
    check(allEligible);
    std::vector<Skill> protectedSkills = {
        {"species_human", 0, {}}, {"social_language_basic_speak", 0, {}},
        {"pilot_rebel_navy_novice", 15, {}}, {"force_title_jedi_rank_02", 1, {}},
        {"admin_general_novice", 15, {}}, {"social_dance", 0, {}},
        {"hidden_innate", 0, {}}, {"combat_secret_master", 1, {}, true}
    };
    bool allProtected = !isPlayerSurrenderableSkill(nullptr);
    for (auto& skill : protectedSkills) allProtected &= !isPlayerSurrenderableSkill(&skill);
    check(allProtected);
    SkillManager manager;
    CreatureObject player;
    Vector<String> result;
    String error;
    std::vector<Skill> owned;
    auto setup = [&](std::vector<Skill> fixture) {
        owned = std::move(fixture); player.owned.removeAll();
        for (auto& skill : owned) player.owned.add(&skill);
        result = {"previous_result"}; error = "previous_error";
        *JediManager::instance() = JediManager();
    };
    setup({{"social_entertainer_novice", 0, {}},
        {"social_entertainer_dance_01", 0, {"social_entertainer_novice"}},
        {"social_dancer_novice", 15, {"social_entertainer_dance_01"}}});
    const Vector<String> cascade = {"social_dancer_novice", "social_entertainer_dance_01", "social_entertainer_novice"};
    check(manager.buildSurrenderSkillPlan(&player, "social_entertainer_novice", result, error) && result == cascade && error.isEmpty());
    check(JediManager::instance()->checked.size() == 1 && JediManager::instance()->checked[0] == cascade);
    JediManager::instance()->rejected = "social_dancer_novice";
    check(!manager.buildSurrenderSkillPlan(&player, "social_entertainer_novice", result, error) && result.empty() && !error.isEmpty());
    setup(protectedSkills);
    check(!manager.buildSurrenderSkillPlan(&player, "all", result, error) && result.empty() && !error.isEmpty());
    owned = zeroCost;
    owned.insert(owned.end(), protectedSkills.begin(), protectedSkills.end());
    setup(owned);
    check(manager.buildSurrenderSkillPlan(&player, "all", result, error) && result.size() == 6);
    bool onlyEligible = true;
    for (const auto& skill : zeroCost) onlyEligible &= result.contains(skill.name);
    check(onlyEligible);
    setup({{"combat_basic_novice", 0, {}}, {"combat_basic_01", 1, {"combat_basic_novice"}},
        {"force_title_jedi_rank_02", 0, {"combat_basic_01"}}, {"social_politician_novice", 0, {}}});
    check(!manager.buildSurrenderSkillPlan(&player, "combat_basic_novice", result, error) && result.empty());
    check(manager.buildSurrenderSkillPlan(&player, "all", result, error) && result == Vector<String>{"social_politician_novice"});
    setup({{"force_sensitive_test_novice", 0, {}},
        {"force_sensitive_test_01", 1, {"force_sensitive_test_novice"}},
        {"force_sensitive_test_02", 1, {"force_sensitive_test_01"}}, {"social_politician_novice", 0, {}}});
    JediManager::instance()->rejected = "force_sensitive_test_02";
    check(manager.buildSurrenderSkillPlan(&player, "all", result, error) && result == Vector<String>{"social_politician_novice"});
    JediManager::instance()->rejected = "";
    JediManager::instance()->forceLimit = 1;
    check(manager.buildSurrenderSkillPlan(&player, "all", result, error) &&
        result == Vector<String>({"force_sensitive_test_02", "social_politician_novice"}));
    check(!manager.buildSurrenderSkillPlan(&player, "unknown_novice", result, error) && result.empty());
    std::cout << passed << " surrender eligibility/adapter checks passed\n";
}
'''


def main():
    source = (CORE / "src/server/zone/managers/skill/SkillManager.cpp").read_text()
    eligibility = function(source, "bool isPlayerSurrenderableSkill(")
    adapter = function(source, "bool SkillManager::buildSurrenderSkillPlan(")
    header = (CORE / "src/server/zone/managers/skill/SkillSurrenderPlan.h").read_text()
    with tempfile.TemporaryDirectory(prefix="surrender-adapter-", dir=CORE / "bin") as folder:
        cpp = Path(folder) / "check.cpp"
        executable = Path(folder) / "check"
        cpp.write_text(header + MOCKS + eligibility + "\n" + adapter + TESTS)
        compiler = shlex.split(os.environ.get("CXX", "g++"))
        subprocess.run(compiler + ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", str(cpp), "-o", str(executable)], check=True, timeout=30)
        subprocess.run([str(executable)], check=True, timeout=10)


if __name__ == "__main__":
    main()
