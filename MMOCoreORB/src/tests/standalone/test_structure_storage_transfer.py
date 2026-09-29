#!/usr/bin/env python3
"""Test actual player-transfer storage guards with standard-library lock mocks.

Extracts the production RAII helper, ancestry classifier, acquisition/recheck,
and commit/release blocks. Admission, transfer effects and lot removal are small
test boundaries; real object locking, callbacks and persistence require Core3
runtime verification. No Core3 or engine3 components are compiled.
"""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]
SOURCE = CORE / "src/server/zone/objects/creature/commands/TransferItemMiscCommand.h"


def block(source, signature):
    start = source.index(signature)
    end = source.index("{", start) + 1
    depth = 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


HARNESS = r'''
#include <atomic>
#include <cstdlib>
#include <functional>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
template<class T> struct ManagedReference {
    T value;
    ManagedReference(T value = nullptr): value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
    ManagedReference& operator=(T next) { value = next; return *this; }
};
template<class T, class U> T cast(U* value) { return dynamic_cast<T>(value); }
struct SceneObject {
    SceneObject* root = nullptr;
    SceneObject* secondRoot = nullptr;
    bool changeOnSecondRead = false;
    int rootReads = 0;
    virtual ~SceneObject() {}
    virtual bool isBuildingObject() const { return false; }
    SceneObject* getRootParent() {
        ++rootReads;
        if (changeOnSecondRead && rootReads == 2) root = secondRoot;
        return root;
    }
};
struct BuildingObject : SceneObject {
    std::recursive_mutex mutex;
    std::atomic<int> attempts{0};
    std::atomic<int> acquisitions{0};
    std::atomic<int> depth{0};
    bool staticBuilding = false;
    int baseLots = 2;
    int items = 5;
    int capacity = 6;
    bool isBuildingObject() const override { return true; }
    bool isStaticBuilding() const { return staticBuilding; }
    int getBaseLotSize() const { return baseLots; }
    bool tryWLock() {
        ++attempts;
        if (!mutex.try_lock()) return false;
        ++acquisitions; ++depth;
        return true;
    }
    void unlock() { --depth; mutex.unlock(); }
};
struct Creature {
    int messages = 0;
    void sendSystemMessage(const char*) { ++messages; }
};
struct Transaction {
    bool aborted = false;
    std::string reason;
    Transaction& abort() { aborted = true; return *this; }
    Transaction& operator<<(const char* value) { reason += value; return *this; }
};
enum { SUCCESS = 0, GENERALERROR = 1 };
HELPER_CLASS;
ANCESTRY_METHOD
struct ObjectController {
    bool succeed = true;
    bool throwOnTransfer = false;
    int calls = 0;
    std::function<void()> duringTransfer;
    bool transferObject(SceneObject*, SceneObject* destination, int, bool) {
        ++calls;
        if (duringTransfer) duringTransfer();
        if (throwOnTransfer) throw std::runtime_error("transfer failed");
        if (!succeed) return false;
        auto building = dynamic_cast<BuildingObject*>(destination->root);
        if (building) ++building->items;
        return true;
    }
};
struct Scenario {
    Creature creature;
    Transaction transaction;
    ObjectController controller;
    bool earlyFailure = false;
    std::function<void()> beforeFinalCheck;
    std::function<void()> observer;
};
int guardedTransfer(SceneObject* objectToTransfer, SceneObject* destinationObject, Scenario& scenario) {
    Creature* creature = &scenario.creature;
    Transaction& trx = scenario.transaction;
    ObjectController* objectController = &scenario.controller;
    int transferType = -1;
    ACQUIRE_BLOCK
    if (scenario.earlyFailure) return GENERALERROR;
    // Admission boundary; production capacity arithmetic is tested separately.
    auto destination = dynamic_cast<BuildingObject*>(destinationObject->root);
    if (destination && destination->items + 1 > destination->capacity) return GENERALERROR;
    // Models the final source Locker yielding/reacquiring before its recheck.
    if (scenario.beforeFinalCheck) scenario.beforeFinalCheck();
    COMMIT_BLOCK
    if (scenario.observer) scenario.observer();
    return SUCCESS;
}
int checks = 0;
void check(bool passed, const char* label) {
    ++checks;
    if (!passed) { std::cerr << "Failed: " << label << '\n'; std::exit(1); }
}
void classificationCases() {
    SceneObject source, destination, pob;
    Scenario scenario;
    check(guardedTransfer(&source, &destination, scenario) == SUCCESS, "objects outside buildings need no guard");
    for (int mode = 0; mode < 3; ++mode) {
        BuildingObject building;
        building.staticBuilding = mode == 0;
        building.baseLots = mode == 1 ? 0 : 2;
        source.root = destination.root = mode == 2 ? &pob : &building;
        Scenario attempt;
        check(guardedTransfer(&source, &destination, attempt) == SUCCESS, "static/zero-lot/POB transfers remain unguarded");
        check(building.attempts == 0, "excluded building never acquires storage lock");
    }
    BuildingObject building;
    source.root = destination.root = &building;
    Scenario same;
    same.controller.duringTransfer = [&] { check(building.depth == 1, "same-building transfer holds one guard through commit"); };
    same.observer = [&] { check(building.depth == 0, "guard released before observers"); };
    check(guardedTransfer(&source, &destination, same) == SUCCESS, "same-building outgoing/inventory ancestry admitted");
    check(building.attempts == 1 && building.acquisitions == 1 && building.depth == 0, "same building acquired once and released once");
    BuildingObject other;
    destination.root = &other;
    Scenario different;
    different.controller.duringTransfer = [&] { check(building.depth == 1 && other.depth == 1, "both building guards held through cross-building commit"); };
    check(guardedTransfer(&source, &destination, different) == SUCCESS, "distinct building transfer admitted");
    check(building.depth == 0 && other.depth == 0, "distinct building guards released");
}
void busyCases() {
    for (int mode = 0; mode < 2; ++mode) {
        BuildingObject first, second;
        SceneObject source, destination;
        source.root = &first; destination.root = &second;
        BuildingObject& busy = mode == 0 ? first : second;
        std::promise<void> ready, release;
        auto released = release.get_future();
        std::thread blocker([&] { std::lock_guard<std::recursive_mutex> lock(busy.mutex); ready.set_value(); released.wait(); });
        ready.get_future().wait();
        Scenario scenario;
        check(guardedTransfer(&source, &destination, scenario) == GENERALERROR, "busy building rejected without waiting");
        check(scenario.creature.messages == 1 && scenario.controller.calls == 0, "busy rejection informs user without transfer");
        check(first.depth == 0 && second.depth == 0, "failed second acquisition releases first guard");
        check(second.attempts == (mode == 0 ? 0 : 1), "failed source acquisition short-circuits destination");
        release.set_value(); blocker.join();
    }
}
void cleanupCases() {
    for (int mode = 0; mode < 4; ++mode) {
        BuildingObject building;
        SceneObject source, destination;
        destination.root = &building;
        Scenario scenario;
        scenario.earlyFailure = mode == 0;
        scenario.controller.succeed = mode != 1;
        scenario.controller.throwOnTransfer = mode == 2;
        if (mode == 3) scenario.beforeFinalCheck = [] { throw std::runtime_error("validation failed"); };
        bool rejected = false;
        try { rejected = guardedTransfer(&source, &destination, scenario) == GENERALERROR; }
        catch (const std::runtime_error&) { rejected = true; }
        check(rejected, "validation/transfer failure or exception exits guarded operation");
        check(building.depth == 0 && building.items == 5, "RAII releases locks without insertion on every failure");
    }
    for (int mode = 0; mode < 4; ++mode) {
        BuildingObject first, second;
        SceneObject source, destination;
        source.root = destination.root = &first;
        SceneObject& changing = mode % 2 ? destination : source;
        Scenario scenario;
        if (mode < 2) { changing.changeOnSecondRead = true; changing.secondRoot = &second; }
        else scenario.beforeFinalCheck = [&] { changing.root = &second; };
        check(guardedTransfer(&source, &destination, scenario) == GENERALERROR, "initial or final ancestry change rejected");
        check(scenario.controller.calls == 0 && first.depth == 0 && second.depth == 0, "ancestry failure cannot commit and releases original guard");
    }
}
void concurrentCases() {
    BuildingObject building;
    SceneObject source, destination;
    destination.root = &building;
    std::promise<void> removalStarted;
    std::thread removal;
    bool removalAccepted = false;
    Scenario scenario;
    scenario.controller.duringTransfer = [&] {
        removal = std::thread([&] {
            removalStarted.set_value();
            std::lock_guard<std::recursive_mutex> lock(building.mutex);
            if (building.items <= 5) { building.capacity = 5; removalAccepted = true; }
        });
        removalStarted.get_future().wait();
        check(building.depth == 1, "insertion retains guard while competing removal waits");
    };
    check(guardedTransfer(&source, &destination, scenario) == SUCCESS, "insertion that acquires guard first completes");
    removal.join();
    check(!removalAccepted && building.items == 6 && building.capacity == 6, "removal sees committed insertion and cannot undercut used storage");
    check(building.items <= building.capacity, "insertion-first race ends within capacity");
    BuildingObject reduced;
    destination.root = &reduced;
    std::promise<void> ready, release;
    auto released = release.get_future();
    std::thread reducer([&] {
        std::lock_guard<std::recursive_mutex> lock(reduced.mutex);
        reduced.capacity = 5;
        ready.set_value(); released.wait();
    });
    ready.get_future().wait();
    Scenario busy;
    check(guardedTransfer(&source, &destination, busy) == GENERALERROR, "removal-first race rejects concurrent insertion as busy");
    release.set_value(); reducer.join();
    Scenario retry;
    check(guardedTransfer(&source, &destination, retry) == GENERALERROR, "retry rechecks reduced capacity");
    check(reduced.items == 5 && reduced.capacity == 5 && reduced.depth == 0, "removal-first race retains existing items within limit");
}
int main() {
    classificationCases(); busyCases(); cleanupCases(); concurrentCases();
    std::cout << checks << " storage transfer guard and concurrency checks passed\n";
}
'''


def main():
    source = SOURCE.read_text()
    command = block(source, "int static doTransferItemMisc(")
    acquire = command[command.index("// Serialize capacity changes"):command.index("if (destinationObject->isIntangibleObject())")]
    final_start = command.index("// Cross-locking the source")
    final_end = command.index("if (clearWeapon)", final_start)
    commit = command[final_start:final_end]
    acquisition = command.index("sourceStorageLock.acquire")
    admission = command.index("destinationObject->canAddObject")
    transfer = command.index("objectController->transferObject")
    first_locker = command.index("Locker ")
    assert command.index("objectToTransfer == nullptr") < acquisition
    assert command.index("destinationObject == nullptr") < acquisition
    assert acquisition < first_locker < admission < transfer
    assert command.index("Locker clocker(objectsParent, creature)") < final_start < transfer
    assert transfer < command.index("destinationStorageLock.release();") < command.index("if (clearWeapon)")
    assert transfer < command.index("sourceStorageLock.release();") < command.index("if (notifyLooted)")
    assert "tryWLock()" in block(source, "class StorageBuildingLock")
    assert "getParentRecursively" not in block(source, "static BuildingObject* getStorageBuilding(")
    print("8 storage transfer lock-order and integration checks passed")
    harness = HARNESS.replace("HELPER_CLASS", block(source, "class StorageBuildingLock"))
    harness = harness.replace("ANCESTRY_METHOD", block(source, "static BuildingObject* getStorageBuilding("))
    harness = harness.replace("ACQUIRE_BLOCK", acquire).replace("COMMIT_BLOCK", commit)
    with tempfile.TemporaryDirectory(prefix="structure-storage-transfer-", dir=CORE / "bin") as temporary:
        cpp, binary = Path(temporary) / "transfer.cpp", Path(temporary) / "transfer"
        cpp.write_text(harness)
        subprocess.run(shlex.split(os.environ.get("CXX", "g++")) + ["-std=c++11", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                       "-fsanitize=undefined", "-fno-sanitize-recover=undefined", "-pthread", str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=20)


if __name__ == "__main__":
    main()
