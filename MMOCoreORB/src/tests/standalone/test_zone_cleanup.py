#!/usr/bin/env python3
"""Test production close-object cleanup helpers and their container call arguments.

Requires Python 3 and a C++17 compiler (CXX or g++). Extracts only the two helper
bodies and container call statements into standard-library mocks. No Core3 or
engine3 headers, libraries, components, or executable are built or run. Temporary
files remain under bin and are removed on exit. --source-head exercises the
current commit as a regression baseline; before the fix is committed it fails.

Limits: relation removal, snapshots, and exceptions are modeled. These tests do
not verify engine containers, real locking/concurrency, observer callbacks,
persistence, full shutdown integrity, or elapsed shutdown time.
"""

import argparse
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


CORE_ROOT = Path(__file__).resolve().parents[3]
ZONE_PATH = Path("src/server/zone")


def extract_helper(source, component):
    start = source.index(f"void {component}::removeAllObjectsFromCOV(")
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


MOCKS = r'''
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
struct SceneObject;
using TreeEntry = SceneObject;
template <typename T> using ManagedReference = T;
template <typename T> struct SortedVector : std::vector<T> {
    void removeAll() { this->clear(); }
};
struct ArrayIndexOutOfBoundsException {
    std::string getMessage() const { return "modeled removal failure"; }
};
struct Logger {
    static Logger console;
    void error(const std::string&) {}
};
Logger Logger::console;
struct CloseObjectsVector {
    std::vector<TreeEntry*> entries;
    int copies = 0;
    int size() const { return static_cast<int>(entries.size()); }
    void safeCopyTo(SortedVector<ManagedReference<TreeEntry*>>& target) {
        ++copies;
        target.assign(entries.begin(), entries.end());
    }
};
struct SceneObject {
    CloseObjectsVector close;
    bool hasCOV = true, stuck = false, throws = false;
    int removals = 0, exceptionsRemaining = 0;
    TreeEntry* appendAfterRemoval = nullptr;
    CloseObjectsVector* getCloseObjects() { return hasCOV ? &close : nullptr; }
    void removeInRangeObject(TreeEntry* other, bool = true) {
        if (other == nullptr) return;
        ++removals;
        if (throws) throw ArrayIndexOutOfBoundsException{};
        if (exceptionsRemaining > 0) {
            --exceptionsRemaining;
            throw ArrayIndexOutOfBoundsException{};
        }
        if (!stuck) {
            auto& entries = close.entries;
            entries.erase(std::remove(entries.begin(), entries.end(), other), entries.end());
            if (appendAfterRemoval) {
                entries.push_back(appendAfterRemoval);
                appendAfterRemoval = nullptr;
            }
        }
    }
    bool contains(TreeEntry* other) const {
        return std::find(close.entries.begin(), close.entries.end(), other) != close.entries.end();
    }
};
using Snapshot = SortedVector<ManagedReference<TreeEntry*>>;
using Helper = void (*)(CloseObjectsVector*, Snapshot&, SceneObject*, SceneObject*);
using ContainerCall = void (*)(SceneObject*, SceneObject*);
struct GroundZoneComponent {
    static void removeAllObjectsFromCOV(CloseObjectsVector*, Snapshot&, SceneObject*, SceneObject*);
};
struct SpaceZoneComponent {
    static void removeAllObjectsFromCOV(CloseObjectsVector*, Snapshot&, SceneObject*, SceneObject*);
};
'''

CASES = r'''
int exercise(const char* name, Helper cleanup, ContainerCall containerCall) {
    const char* names[] = {"owned reciprocal removal", "borrowed parent list",
        "empty list", "owned self/null/no-COV entries", "borrowed self/null/no-COV entries",
        "owned stalled removal bound", "owned exception bound", "container removal target",
        "owned new entry during removal", "owned transient exception"};
    int failures = 0;
    for (int scenario = 0; scenario < 10; ++scenario) {
        SceneObject object, neighbor, unrelated, parent, zone, noCOV;
        noCOV.hasCOV = false;
        Snapshot snapshot;
        auto clean = [&](SceneObject& owner) { cleanup(&owner.close, snapshot, &object, &owner); };
        try {
            switch (scenario) {
            case 0:
                object.close.entries = {&neighbor};
                neighbor.close.entries = {&object, &unrelated};
                clean(object);
                require(object.close.size() == 0 && !neighbor.contains(&object), "stale reciprocal link");
                require(neighbor.contains(&unrelated), "unrelated neighbor link removed");
                clean(object);
                require(object.close.copies == 1 && neighbor.removals == 1, "redundant owned work");
                break;
            case 1:
                parent.close.entries = {&neighbor, &unrelated};
                neighbor.close.entries = {&object, &parent, &unrelated};
                unrelated.close.entries = {&parent, &object};
                clean(parent);
                std::cout << name << " borrowed: " << parent.close.copies << " snapshots, "
                          << neighbor.removals + unrelated.removals << " neighbor removals\n";
                require(parent.close.entries == std::vector<TreeEntry*>({&neighbor, &unrelated}),
                        "parent neighbor list changed");
                require(!neighbor.contains(&object) && !unrelated.contains(&object), "child link retained");
                require(neighbor.contains(&parent) && neighbor.contains(&unrelated)
                        && unrelated.contains(&parent), "unrelated links removed");
                require(parent.close.copies == 1 && neighbor.removals == 1 && unrelated.removals == 1,
                        "borrowed list rescanned despite remaining parent entries");
                break;
            case 2:
                clean(object);
                clean(parent);
                require(object.close.copies == 0 && parent.close.copies == 0, "empty list copied");
                break;
            case 3: case 4: {
                SceneObject& owner = scenario == 3 ? object : parent;
                owner.close.entries = {&object, nullptr, &noCOV, &neighbor};
                neighbor.close.entries = {&object, &unrelated};
                auto original = owner.close.entries;
                clean(owner);
                require(noCOV.removals == 0 && neighbor.removals == 1, "invalid/repeated neighbor removal");
                require(!neighbor.contains(&object) && neighbor.contains(&unrelated), "wrong neighbor result");
                // Null removal is a no-op: retain the existing owned-list retry cap.
                require(scenario == 3 ? owner.close.entries == std::vector<TreeEntry*>({nullptr})
                                      : owner.close.entries == original,
                        "non-null owned entry retained or borrowed list altered");
                require(owner.close.copies == (scenario == 3 ? 100 : 1), "wrong edge-entry retry bound");
                break;
            }
            case 5: case 6:
                object.close.entries = {&neighbor};
                neighbor.close.entries = {&object};
                object.stuck = scenario == 5;
                object.throws = scenario == 6;
                clean(object);
                require(object.close.copies == 100 && object.removals == 100, "owned retry bound changed");
                require(object.contains(&neighbor) && !neighbor.contains(&object), "unexpected retry state");
                break;
            case 7:
                object.close.entries = {&neighbor};
                neighbor.close.entries = {&object, &zone, &unrelated};
                containerCall(&zone, &object);
                std::cout << name << " container: " << object.close.copies << " snapshots, "
                          << neighbor.removals << " neighbor removals\n";
                require(!neighbor.contains(&object), "container removed zone instead of departing object");
                require(object.close.size() == 0, "container left departing object's list populated");
                require(neighbor.contains(&zone) && neighbor.contains(&unrelated), "container removed unrelated link");
                require(object.close.copies == 1 && neighbor.removals == 1, "redundant container cleanup");
                break;
            case 8: case 9:
                object.close.entries = {&neighbor};
                neighbor.close.entries = {&object};
                unrelated.close.entries = {&object};
                if (scenario == 8) object.appendAfterRemoval = &unrelated;
                else object.exceptionsRemaining = 1;
                clean(object);
                require(object.close.size() == 0 && !neighbor.contains(&object), "retry did not complete cleanup");
                require(object.close.copies == 2, "owned cleanup did not resnapshot for retry");
                if (scenario == 8) require(!unrelated.contains(&object), "new neighbor reference retained");
                break;
            }
            require(snapshot.empty(), "scratch snapshot retained references");
            std::cout << "PASS " << name << ": " << names[scenario] << '\n';
        } catch (const std::exception& error) {
            ++failures;
            std::cout << "FAIL " << name << ": " << names[scenario] << ": " << error.what() << '\n';
        }
    }
    return failures;
}
int main() {
    int failures = exercise("ground", GroundZoneComponent::removeAllObjectsFromCOV, groundCall)
                 + exercise("space", SpaceZoneComponent::removeAllObjectsFromCOV, spaceCall);
    std::cout << 20 - failures << " passed, " << failures << " failed\n";
    return failures == 0 ? 0 : 1;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", action="store_true", help="exercise current HEAD instead of working source")
    args = parser.parse_args()

    def read(path):
        if args.source_head:
            return subprocess.run(["git", "show", f"HEAD:MMOCoreORB/{path.as_posix()}"],
                                  cwd=CORE_ROOT, check=True, capture_output=True, text=True).stdout
        return (CORE_ROOT / path).read_text()

    program = MOCKS
    for kind in ("Ground", "Space"):
        component = f"{kind}ZoneComponent"
        program += extract_helper(read(ZONE_PATH / f"objects/scene/components/{component}.cpp"), component)
        container = read(ZONE_PATH / f"{kind}ZoneContainerComponent.cpp")
        calls = re.findall(rf"{component}::removeAllObjectsFromCOV\([^;]+\);", container)
        if len(calls) != 1:
            raise ValueError(f"Expected exactly one cleanup call in {kind} container")
        program += f"""
void {kind.lower()}Call([[maybe_unused]] SceneObject* sceneObject, SceneObject* object) {{
    auto* closeObjects = object->getCloseObjects();
    Snapshot closeSceneObjects;
    {calls[0]}
    require(closeSceneObjects.empty(), "container scratch snapshot retained references");
}}
"""
    program += CASES
    compiler = shlex.split(os.environ.get("CXX", "g++"))
    with tempfile.TemporaryDirectory(prefix=".zone-cleanup-test-", dir=CORE_ROOT / "bin") as temporary:
        directory = Path(temporary)
        source, executable = directory / "test.cpp", directory / "test"
        source.write_text(program)
        subprocess.run([*compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
                        str(source), "-o", str(executable)], check=True, timeout=30)
        print("Source: current HEAD" if args.source_head else "Source: working tree", flush=True)
        return subprocess.run([str(executable)], timeout=10).returncode


if __name__ == "__main__":
    raise SystemExit(main())
