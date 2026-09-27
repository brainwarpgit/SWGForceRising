#!/usr/bin/env python3
"""Exercise the production skill-surrender dependency planner in isolation.

Run with Python 3; requires a C++17 compiler (CXX or g++). Only the planner's
standard-library header and this harness are compiled. No Core3 components,
engine3 files, or executable are built or run. Temporary files remain under
bin and are removed on exit.

The planner receives synthetic owned-skill data. These tests verify dependency
closure, protection, safe ordering, and deterministic results; they do not
verify live skill data, UI callbacks, gameplay restrictions, actual skill-point
refunds, save/load, or any Core3 runtime behavior.
"""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE_ROOT = Path(__file__).resolve().parents[3]
HEADER_PATH = CORE_ROOT / "src/server/zone/managers/skill/SkillSurrenderPlan.h"

CASES = r'''
#include <algorithm>
#include <functional>
#include <iostream>
#include <stdexcept>

using SkillSurrenderPlan::Node;
using SkillSurrenderPlan::Result;
using SkillSurrenderPlan::build;
using Nodes = std::vector<Node>;
using Names = std::vector<std::string>;

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
void expect(const Result& result, const Names& names) {
    require(result.error.empty(), result.error.c_str());
    require(result.skills == names, "unexpected removal order or membership");
}
void expectError(const Result& result) {
    require(!result.error.empty(), "unsafe or invalid request accepted");
    require(result.skills.empty(), "error returned a partial removal plan");
}
void checkSafe(const Nodes& owned, const Result& result) {
    require(result.error.empty(), result.error.c_str());
    std::set<std::string> remaining;
    for (const auto& node : owned) remaining.insert(node.name);
    for (const auto& name : result.skills) {
        auto node = std::find_if(owned.begin(), owned.end(), [&](const Node& n) {
            return n.name == name;
        });
        require(node != owned.end() && node->eligible, "removed unknown or protected skill");
        require(remaining.erase(name) == 1, "removed skill twice");
        for (const auto& retained : owned) {
            if (remaining.count(retained.name) == 0) continue;
            require(std::find(retained.required.begin(), retained.required.end(), name)
                        == retained.required.end(), "removed a prerequisite before its dependent");
        }
    }
}

const Nodes entertainer = {
    {"entertainer_novice", {}, true},
    {"entertainer_dance_04", {"entertainer_novice"}, true},
    {"entertainer_music_04", {"entertainer_novice"}, true},
    {"dancer_novice", {"entertainer_dance_04"}, true},
    {"dancer_master", {"dancer_novice"}, true},
    {"musician_novice", {"entertainer_music_04"}, true},
    {"musician_master", {"musician_novice"}, true},
    {"artisan_novice", {}, true},
};

// Exhaustively inspect all four-node DAGs and eligibility assignments. The
// independent oracle enumerates every possible safe removal subset rather
// than reproducing the planner's graph walk or topological sort.
void exhaustiveGraphs() {
    const Names names = {"a", "b", "c", "d"};
    for (unsigned edges = 0; edges < 64; ++edges) {
        for (unsigned eligibility = 0; eligibility < 16; ++eligibility) {
            Nodes owned;
            for (unsigned i = 0; i < 4; ++i)
                owned.push_back({names[i], {}, (eligibility & (1U << i)) != 0});
            unsigned edge = 0;
            for (unsigned dependent = 1; dependent < 4; ++dependent) {
                for (unsigned prerequisite = 0; prerequisite < dependent; ++prerequisite) {
                    if (edges & (1U << edge))
                        owned[dependent].required.push_back(names[prerequisite]);
                    ++edge;
                }
            }
            std::vector<unsigned> safe;
            for (unsigned subset = 0; subset < 16; ++subset) {
                if (subset & ~eligibility) continue;
                bool valid = true;
                for (unsigned i = 0; i < 4; ++i) {
                    if (subset & (1U << i)) continue;
                    for (unsigned j = 0; j < 4; ++j) {
                        if ((subset & (1U << j)) &&
                            std::find(owned[i].required.begin(), owned[i].required.end(), names[j])
                                != owned[i].required.end()) valid = false;
                    }
                }
                if (valid) safe.push_back(subset);
            }
            auto mask = [&](const Result& result) {
                unsigned removed = 0;
                for (const auto& name : result.skills) {
                    auto found = std::find(names.begin(), names.end(), name);
                    require(found != names.end(), "unknown result name");
                    removed |= 1U << std::distance(names.begin(), found);
                }
                return removed;
            };
            auto all = build(owned, "", true);
            checkSafe(owned, all);
            for (auto subset : safe)
                require((subset & ~mask(all)) == 0, "all omitted a safely removable skill");
            for (unsigned root = 0; root < 4; ++root) {
                unsigned intersection = 15;
                bool found = false;
                for (auto subset : safe) {
                    if (!(subset & (1U << root))) continue;
                    intersection &= subset;
                    found = true;
                }
                auto result = build(owned, names[root], false);
                if (!found) expectError(result);
                else {
                    checkSafe(owned, result);
                    require(mask(result) == intersection, "selection removed too many or too few skills");
                }
            }
        }
    }
}

int main() {
    const std::vector<std::pair<const char*, std::function<void()>>> tests = {
        {"novice entertainer includes dancer and musician professions", [] {
            auto result = build(entertainer, "entertainer_novice", false);
            expect(result, {"dancer_master", "dancer_novice", "entertainer_dance_04",
                            "musician_master", "musician_novice", "entertainer_music_04",
                            "entertainer_novice"});
            checkSafe(entertainer, result);
        }},
        {"selected leaf preserves its prerequisites and other professions", [] {
            expect(build(entertainer, "dancer_master", false), {"dancer_master"});
        }},
        {"selected branch preserves sibling branches", [] {
            expect(build(entertainer, "entertainer_dance_04", false),
                   {"dancer_master", "dancer_novice", "entertainer_dance_04"});
        }},
        {"shared requirements and diamonds remove each dependent once", [] {
            Nodes nodes = {{"a", {}, true}, {"b", {"a"}, true},
                           {"c", {"a"}, true}, {"d", {"b", "c"}, true}};
            expect(build(nodes, "a", false), {"d", "b", "c", "a"});
            expect(build(nodes, "b", false), {"d", "b"});
        }},
        {"protected direct dependent blocks a selection", [] {
            expectError(build({{"a", {}, true}, {"b", {"a"}, false}}, "a", false));
        }},
        {"protected transitive dependent blocks a selection", [] {
            expectError(build({{"a", {}, true}, {"b", {"a"}, true},
                               {"c", {"b"}, false}}, "a", false));
        }},
        {"all preserves protected prerequisites transitively", [] {
            Nodes nodes = {{"a", {}, true}, {"b", {"a"}, true},
                           {"protected", {"b"}, false}, {"c", {"a"}, true},
                           {"d", {"c"}, true}, {"unrelated", {}, true}};
            auto result = build(nodes, "ignored", true);
            expect(result, {"d", "c", "unrelated"});
            checkSafe(nodes, result);
        }},
        {"all may remove a dependent of a protected skill", [] {
            expect(build({{"a", {}, false}, {"b", {"a"}, true}}, "", true), {"b"});
        }},
        {"all with only protected skills is empty", [] {
            expect(build({{"a", {}, false}}, "", true), {});
        }},
        {"empty all request is empty", [] { expect(build({}, "", true), {}); }},
        {"unowned or empty root is rejected", [] {
            expectError(build(entertainer, "missing", false));
            expectError(build({}, "", false));
        }},
        {"protected root is rejected", [] {
            expectError(build({{"a", {}, false}}, "a", false));
        }},
        {"unowned prerequisites are ignored", [] {
            expect(build({{"a", {"not_owned"}, true}}, "a", false), {"a"});
        }},
        {"duplicate prerequisite links are harmless", [] {
            expect(build({{"a", {}, true}, {"b", {"a", "a"}, true}}, "a", false), {"b", "a"});
        }},
        {"duplicate owned names are rejected", [] {
            expectError(build({{"a", {}, true}, {"a", {}, true}}, "a", false));
        }},
        {"empty owned name is rejected", [] {
            expectError(build({{"", {}, true}}, "", true));
        }},
        {"cycle returns no partial plan", [] {
            Nodes nodes = {{"a", {"b"}, true}, {"b", {"a"}, true}, {"c", {}, true}};
            expectError(build(nodes, "a", false));
            expectError(build(nodes, "", true));
        }},
        {"self dependency is rejected", [] {
            expectError(build({{"a", {"a"}, true}}, "a", false));
        }},
        {"unrelated cycle does not block a valid selection", [] {
            expect(build({{"a", {"b"}, true}, {"b", {"a"}, true},
                          {"c", {}, true}}, "c", false), {"c"});
        }},
        {"inventory and prerequisite order do not change plans", [] {
            auto shuffled = entertainer;
            auto expected = build(shuffled, "", true);
            std::reverse(shuffled.begin(), shuffled.end());
            for (auto& node : shuffled) std::reverse(node.required.begin(), node.required.end());
            expect(build(shuffled, "", true), expected.skills);
            expect(build(shuffled, "entertainer_novice", false),
                   build(entertainer, "entertainer_novice", false).skills);
        }},
        {"long dependency chain completes without recursion", [] {
            Nodes nodes = {{"0", {}, true}};
            for (int i = 1; i < 4096; ++i)
                nodes.push_back({std::to_string(i), {std::to_string(i - 1)}, true});
            auto result = build(nodes, "0", false);
            require(result.error.empty() && result.skills.size() == 4096, "incomplete long chain");
            require(result.skills.front() == "4095" && result.skills.back() == "0", "wrong long-chain order");
        }},
        {"5120 exhaustive four-skill dependency and eligibility requests", exhaustiveGraphs},
    };
    int failed = 0;
    for (const auto& test : tests) {
        try { test.second(); std::cout << "PASS " << test.first << '\n'; }
        catch (const std::exception& error) {
            ++failed;
            std::cerr << "FAIL " << test.first << ": " << error.what() << '\n';
        }
    }
    std::cout << tests.size() - failed << " passed, " << failed << " failed\n";
    return failed ? 1 : 0;
}
'''


def main():
    compiler = shlex.split(os.environ.get("CXX", "g++"))
    with tempfile.TemporaryDirectory(prefix=".skill-surrender-plan-test-", dir=CORE_ROOT / "bin") as temporary:
        directory = Path(temporary)
        source = directory / "test.cpp"
        executable = directory / "test"
        source.write_text(HEADER_PATH.read_text() + "\n" + CASES)
        subprocess.run(
            [*compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", str(source), "-o", str(executable)],
            check=True,
            timeout=30,
        )
        return subprocess.run([str(executable)], timeout=10).returncode


if __name__ == "__main__":
    raise SystemExit(main())
