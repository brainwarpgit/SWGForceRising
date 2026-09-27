#!/usr/bin/env python3
"""Exercise the production deferred database-insertion task in isolation.

Run with Python 3 from any directory. Requires a C++17 compiler (CXX or g++).
Only the local InsertZoneTask class is extracted from SceneObjectImplementation;
all surrounding types are standard-library mocks. No Core3 headers, libraries,
components, or executable are built or run. Temporary files stay under bin and
are deleted on exit.

Use --source-head to test the task from the current Git HEAD as a regression
baseline. Before the fix is committed, that run is expected to fail.

Limits: these deterministic event orders test the actual task's decision and
locking placement, but storage/recall and container operations are modeled.
They do not verify database serialization, real scheduler/lock behavior,
network messages, player login/dismount, or full Core3 runtime recovery.
"""

import argparse
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import textwrap


CORE_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PATH = Path("src/server/zone/objects/scene/SceneObjectImplementation.cpp")


def extract_task(source):
    function = source.index("void SceneObjectImplementation::notifyLoadFromDatabase() {")
    start = source.index("\t\tclass InsertZoneTask : public Task {", function)
    end = source.index("\n\t\t};", start) + len("\n\t\t};")
    return textwrap.dedent(source[start:end])


MOCKS = r'''
#include <iostream>
#include <stdexcept>
#include <string>

void require(bool value, const char* message) {
    if (!value) throw std::runtime_error(message);
}
class Zone;
struct SceneObject {
    Zone* localZone = nullptr;
    SceneObject* parent = nullptr;
    bool quad = false, octree = false, locked = false, ownerLinked = true;
    int status = 1, insertions = 0;
    Zone* getLocalZone() const {
        require(locked, "zone checked without object lock"); return localZone;
    }
    bool isInQuadTree() const {
        require(locked, "quadtree checked without object lock"); return quad;
    }
    bool isInOctree() const {
        require(locked, "octree checked without object lock"); return octree;
    }
    SceneObject* getParent() const { return parent; }
};
template <typename T> struct Reference {
    T value;
    Reference(T value) : value(value) {}
    T operator->() const { return value; }
    operator T() const { return value; }
};
struct Locker {
    SceneObject* object;
    explicit Locker(SceneObject* object) : object(object) { object->locked = true; }
    ~Locker() { object->locked = false; }
};
struct Task {
    int scheduledCount = 0, delay = 0;
    std::string queue;
    virtual ~Task() = default;
    virtual void run() = 0;
    void setCustomTaskQueue(const char* name) { queue = name; }
    void schedule(int value) { ++scheduledCount; delay = value; }
};
struct ZoneName { const char* toCharArray() const { return "test_zone"; } };
struct Zone {
    bool started = true, space = false;
    ZoneName getZoneName() const { return {}; }
    bool hasManagersStarted() const { return started; }
    void transferObject(SceneObject* object, int arrangement, bool notify) {
        require(object->locked, "insertion without object lock");
        require(arrangement == -1 && notify, "changed insertion arguments");
        object->localZone = this;
        object->parent = nullptr;
        object->quad = !space;
        object->octree = space;
        ++object->insertions;
    }
};
// Only model state relevant to the actual task's insertion decision.
void store(SceneObject& object) {
    object.localZone = nullptr;
    object.quad = object.octree = object.ownerLinked = false;
    object.status = 0;
}
void insert(SceneObject& object, Zone& zone) {
    Locker lock(&object);
    object.ownerLinked = true;
    object.status = 1;
    zone.transferObject(&object, -1, true);
}
'''

CASES = r'''
int main() {
    const char* names[] = {
        "normal ground restore", "normal space restore", "wait for managers",
        "store before restore", "store while waiting", "restore before store",
        "same-zone recall", "mounted login direct insertion", "moved zone",
        "space octree duplicate", "parented saved object"
    };
    int failed = 0;
    for (int scenario = 0; scenario < 11; ++scenario) {
        Zone zone, otherZone;
        zone.space = scenario == 1 || scenario == 9;
        SceneObject object, parent, rider;
        object.localZone = &zone;
        InsertZoneTask task(&object, &zone);
        try {
            switch (scenario) {
            case 0: case 1:
                task.run();
                require(object.insertions == 1, "saved object not inserted");
                require(zone.space ? object.octree : object.quad, "wrong spatial tree");
                break;
            case 2:
                zone.started = false;
                task.run();
                require(task.scheduledCount == 1 && task.delay == 500, "missing manager wait");
                require(object.insertions == 0, "inserted before managers ready");
                zone.started = true;
                task.run();
                require(object.insertions == 1, "not inserted when managers ready");
                break;
            case 3: case 4:
                if (scenario == 4) { zone.started = false; task.run(); }
                store(object);
                zone.started = true;
                task.run();
                require(object.insertions == 0 && object.localZone == nullptr,
                        "stored vehicle reinserted without owner");
                require(!object.ownerLinked && object.status == 0, "stored state disturbed");
                break;
            case 5:
                task.run();
                store(object);
                require(object.insertions == 1 && object.localZone == nullptr && !object.quad,
                        "ordinary restore then store changed");
                break;
            case 6: case 7: case 9:
                if (scenario == 6) store(object);
                if (scenario == 7) rider.parent = &object;
                insert(object, zone);
                task.run();
                require(object.insertions == 1, "duplicate insertion/notification");
                require(object.ownerLinked && object.status == 1, "called state disturbed");
                if (scenario == 7) require(rider.parent == &object, "rider parent disturbed");
                break;
            case 8:
                object.localZone = &otherZone;
                task.run();
                require(object.insertions == 0 && object.localZone == &otherZone,
                        "moved object restored into old zone");
                break;
            case 10:
                object.parent = &parent;
                task.run();
                require(object.insertions == 1, "parent check blocked generic restore path");
                break;
            }
            require(task.queue == "test_zone", "zone queue changed");
            require(!object.locked, "lock not released");
            std::cout << "PASS " << names[scenario] << '\n';
        } catch (const std::exception& error) {
            ++failed;
            std::cout << "FAIL " << names[scenario] << ": " << error.what() << '\n';
        }
    }
    std::cout << 11 - failed << " passed, " << failed << " failed\n";
    return failed == 0 ? 0 : 1;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-head", action="store_true", help="exercise current HEAD instead of the working source")
    args = parser.parse_args()
    if args.source_head:
        source = subprocess.run(
            ["git", "show", f"HEAD:MMOCoreORB/{SOURCE_PATH.as_posix()}"],
            cwd=CORE_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    else:
        source = (CORE_ROOT / SOURCE_PATH).read_text()

    program = MOCKS + "\n" + extract_task(source) + "\n" + CASES
    compiler = shlex.split(os.environ.get("CXX", "g++"))
    with tempfile.TemporaryDirectory(prefix=".vehicle-restore-test-", dir=CORE_ROOT / "bin") as temporary:
        directory = Path(temporary)
        cpp_path = directory / "test.cpp"
        executable = directory / "test"
        cpp_path.write_text(program)
        subprocess.run(
            [*compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", str(cpp_path), "-o", str(executable)],
            check=True,
            timeout=30,
        )
        print("Source: current HEAD" if args.source_head else "Source: working tree", flush=True)
        return subprocess.run([str(executable)], timeout=10).returncode


if __name__ == "__main__":
    raise SystemExit(main())
