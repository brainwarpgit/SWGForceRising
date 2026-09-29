#!/usr/bin/env python3
"""Exercise extracted structure lot methods with the real standalone ledger.

Only standard-library mocks are compiled, never Core3 or engine3. Persistence
declarations and placement/transfer/destruction wiring receive source checks;
these do not substitute for database round-trip or in-game verification.
"""

import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]
STRUCTURE = CORE / "src/server/zone/objects/structure"
MANAGER = CORE / "src/server/zone/managers/structure"


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


HARNESS = r'''
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>
#include "AccountLotLedger.h"
using int64 = std::int64_t;
using uint64 = std::uint64_t;
using Exception = std::runtime_error;
struct SharedObjectTemplate { virtual ~SharedObjectTemplate() {} };
struct SharedStructureObjectTemplate : SharedObjectTemplate {
    std::uint8_t lots;
    explicit SharedStructureObjectTemplate(std::uint8_t value): lots(value) {}
    int getLotSize() const { return lots; }
};
struct NavArea {
    int deletions = 0;
    void destroyObjectFromDatabase(bool) { ++deletions; }
};
struct TangibleObjectImplementation {
    bool deleted = false;
    bool deletedChildren = false;
    void destroyObjectFromDatabase(bool children) { deleted = true; deletedChildren = children; }
};
struct StructureObjectImplementation;
using StructureObject = StructureObjectImplementation;
struct StructureManager {
    AccountLotLedger accountLots;
    static StructureManager* current;
    static StructureManager* instance() { return current; }
    bool updateStructureLotCount(StructureObject* structure, int lots, int accountCapacity);
    bool updateStructureLotOwner(StructureObject* structure, uint64 owner, uint64 reservation);
    void removeStructureLots(uint64 object) { accountLots.removeStructure(object); }
};
StructureManager* StructureManager::current = nullptr;
struct StructureObjectImplementation : TangibleObjectImplementation {
    struct TemplateReference {
        SharedObjectTemplate* value;
        SharedObjectTemplate* get() const { return value; }
    } templateObject;
    struct SelfReference {
        StructureObject* value;
        StructureObject* getReferenceUnsafeStaticCast() const { return value; }
    } _this;
    struct Permissions {
        uint64 owner = 1;
        void setOwner(uint64 value) { owner = value; }
    } structurePermissionList;
    int additionalLots;
    uint64 objectID = 100;
    uint64 ownerObjectID = 1;
    bool building = true;
    bool liveZone = true;
    bool pendingDestruction = false;
    NavArea* navArea = nullptr;
    explicit StructureObjectImplementation(SharedObjectTemplate* value)
        : templateObject{value}, _this{this} { INITIALIZER }
    int getBaseLotSize() const;
    int getLotSize() const;
    int getAdditionalLots() const { return additionalLots; }
    bool setAdditionalLots(int lots, int accountCapacity);
    bool isBuildingObject() const { return building; }
    void* getZone() const { return liveZone ? const_cast<StructureObject*>(this) : nullptr; }
    bool isPendingDestruction() const { return pendingDestruction; }
    uint64 getObjectID() const { return objectID; }
    uint64 getOwnerObjectID() const { return ownerObjectID; }
    void setOwner(uint64 objectID, uint64 lotReservation = 0);
    void destroyObjectFromDatabase(bool destroyContainedObjects = false);
};
MODEL_METHODS
RESIZE_METHOD
// Boundary mock: persisted owner lookup is covered by the bootstrap/transfer tests.
bool StructureManager::updateStructureLotOwner(StructureObject* structure, uint64 owner, uint64 reservation) {
    return accountLots.setStructure(structure->getObjectID(), owner, structure->getLotSize(), reservation);
}
int checks = 0;
void check(bool passed, const char* description) {
    ++checks;
    if (!passed) { std::cerr << "Failed: " << description << '\n'; std::exit(1); }
}
struct Fixture {
    StructureManager manager;
    SharedStructureObjectTemplate templ;
    StructureObject object;
    explicit Fixture(int base = 2): templ(static_cast<std::uint8_t>(base)), object(&templ) {
        StructureManager::current = &manager;
        manager.accountLots.setReady(true);
        check(manager.accountLots.registerOwner(1, 10), "register original owner");
        check(manager.accountLots.registerOwner(2, 10), "register sibling owner");
        check(manager.accountLots.registerOwner(3, 20), "register different account");
        check(manager.accountLots.setStructure(100, 1, base), "initialize base usage");
    }
};
void modelCases() {
    Fixture f;
    check(f.object.additionalLots == 0 && f.object.getLotSize() == 2, "new structure starts at template minimum");
    check(f.object.getBaseLotSize() == 2, "base accessor remains independent");
    check(f.object.setAdditionalLots(3, 10), "ledger approves addition before field changes");
    check(f.object.additionalLots == 3 && f.object.getLotSize() == 5, "successful addition updates persistent field");
    check(f.manager.accountLots.remaining(10, 10) == 5, "addition charges shared account");
    check(!f.object.setAdditionalLots(5, 10), "addition above twice the template lots is denied");
    check(f.object.additionalLots == 3 && f.manager.accountLots.remaining(10, 10) == 5, "denial preserves field and ledger");
    check(f.object.setAdditionalLots(0, 1), "release allowed when account is already over capacity");
    check(f.object.getLotSize() == f.object.getBaseLotSize(), "removal retains template minimum");
    check(!f.object.setAdditionalLots(-1, 10), "negative additional lots rejected");
    check(f.object.additionalLots == 0, "negative request preserves saved value");
    Fixture large(200);
    check(large.object.setAdditionalLots(200, 1000) && large.object.getLotSize() == 400, "total above255 does not truncate");
    check(large.manager.accountLots.remaining(10, 1000) == 600, "ledger charges complete large total");
    StructureManager::current = &f.manager;
    f.object.additionalLots = -9;
    check(f.object.getLotSize() == 2, "read accessor never reduces template cost for invalid negative field");
    f.object.additionalLots = std::numeric_limits<int>::max();
    check(f.object.getLotSize() == std::numeric_limits<int>::max(), "read accessor saturates invalid overflowing saved sum");
    SharedObjectTemplate other;
    f.object.templateObject.value = &other;
    check(f.object.getBaseLotSize() == 0, "nonstructure template has no base lots");
    f.object.templateObject.value = nullptr;
    check(f.object.getBaseLotSize() == 0, "missing template has no base lots");
    Fixture old;
    old.object.additionalLots = 5;
    old.manager.accountLots.setStructure(100, 1, 7);
    check(!old.object.setAdditionalLots(6, 100), "saved over-cap allocation cannot grow");
    check(old.object.setAdditionalLots(4, 100), "saved over-cap allocation can be reduced to the new limit");
}
void validationCases() {
    for (int mode = 0; mode < 6; ++mode) {
        Fixture f;
        if (mode == 0) f.object.building = false;
        if (mode == 1) f.templ.lots = 0;
        if (mode == 2) f.object.templateObject.value = nullptr;
        if (mode == 3) f.object.liveZone = false;
        if (mode == 4) f.object.pendingDestruction = true;
        if (mode == 5) f.manager.accountLots.setReady(false);
        check(!f.object.setAdditionalLots(1, 100), "ineligible or unavailable model denies mutation");
        check(f.object.additionalLots == 0, "ineligible mutation preserves persistent field");
        f.manager.accountLots.setReady(true);
        check(f.manager.accountLots.remaining(10, 100) == 98, "ineligible mutation preserves charged base");
    }
    Fixture f;
    check(!f.object.setAdditionalLots(std::numeric_limits<int>::max(), std::numeric_limits<int>::max()), "reject base-plus-extra overflow");
    check(f.object.additionalLots == 0, "overflow leaves saved value unchanged");
    check(f.object.setAdditionalLots(4, std::numeric_limits<int>::max()), "accept exactly twice the base lots");
    check(f.object.getLotSize() == 6, "maximum total includes base and added lots");
    check(!f.object.setAdditionalLots(5, std::numeric_limits<int>::max()), "reject one added lot beyond the structure cap");
    check(f.object.setAdditionalLots(0, 100), "release from the maximum is safe");
    f.manager.accountLots.setStructure(100, 1, 4);
    check(!f.object.setAdditionalLots(1, 100), "stale ledger cost blocks mutation");
    check(f.object.additionalLots == 0 && f.manager.accountLots.remaining(10, 100) == 96, "stale ledger failure preserves both sides");
}
void lifecycleCases() {
    Fixture f;
    check(f.object.setAdditionalLots(3, 5), "fill entire pool with allocated extras");
    const uint64 pending = f.manager.accountLots.reserve(10, 5, f.object.getLotSize(), 100);
    check(pending != 0, "full same-account pool can reserve title transfer");
    check(!f.object.setAdditionalLots(0, 5), "pending transfer prevents resizing even to lower cost");
    check(f.object.additionalLots == 3, "pending transfer rejection keeps extras");
    f.object.setOwner(2, pending);
    check(f.object.getOwnerObjectID() == 2 && f.object.additionalLots == 3, "actual owner setter retains extras");
    check(f.manager.accountLots.remaining(10, 5) == 0, "same-account transfer retains full total charge");
    check(f.manager.accountLots.reserve(20, 4, f.object.getLotSize(), 100) == 0, "cross-account transfer needs base plus extras");
    const uint64 cross = f.manager.accountLots.reserve(20, 5, f.object.getLotSize(), 100);
    check(cross != 0, "cross-account transfer can reserve entire total");
    f.object.setOwner(3, cross);
    check(f.object.additionalLots == 3 && f.manager.accountLots.remaining(10, 5) == 5, "transfer retains field and refunds original account");
    check(f.manager.accountLots.remaining(20, 5) == 0, "recipient charged all lots");
    f.object.pendingDestruction = true;
    check(!f.object.setAdditionalLots(0, 5), "queued destruction freezes allocation");
    bool threw = false;
    try { f.object.setOwner(2); } catch (const Exception&) { threw = true; }
    check(threw && f.object.ownerObjectID == 3, "pending deletion blocks ownership transfer");
    NavArea nav;
    f.object.navArea = &nav;
    f.object.destroyObjectFromDatabase(true);
    check(f.object.deleted && f.object.deletedChildren && nav.deletions == 1, "actual database destructor delegates object cleanup");
    check(f.manager.accountLots.remaining(20, 5) == 5, "database destruction releases base plus extras");
    f.object.destroyObjectFromDatabase(true);
    check(f.manager.accountLots.remaining(20, 5) == 5, "repeated cleanup cannot double-refund");
    StructureObject replacement(&f.templ);
    replacement.objectID = 101;
    const uint64 placement = f.manager.accountLots.reserve(10, 5, replacement.getBaseLotSize());
    check(placement != 0, "redeeded template can reserve normal placement");
    replacement.setOwner(1, placement);
    check(replacement.additionalLots == 0 && replacement.getLotSize() == 2, "new placement does not inherit prior allocation");
    check(f.manager.accountLots.remaining(10, 5) == 3, "new placement charges base only");
}
int main() {
    modelCases(); validationCases(); lifecycleCases();
    std::cout << checks << " structure lot model/ledger/lifecycle checks passed\n";
}
'''


def main():
    source = (STRUCTURE / "StructureObjectImplementation.cpp").read_text()
    idl = (STRUCTURE / "StructureObject.idl").read_text()
    manager = (MANAGER / "StructureManager.cpp").read_text()
    constructor = function(idl, "public StructureObject()")
    initializer = re.search(r"\badditionalLots\s*=\s*0\s*;", constructor)
    assert initializer, "New and legacy structures require a zero additional-lot default"
    assert re.search(r"protected int additionalLots;", idl), "Additional lots must be persisted signed int"
    assert "additionalLots" not in function(source, "void StructureObjectImplementation::initializeTransientMembers()"), "Loading must preserve saved allocation"
    bootstrap = function(manager, "void StructureManager::initializeAccountLots()")
    assert 'STRING_HASHCODE("StructureObject.additionalLots")' in bootstrap
    assert "structureTemplate->getLotSize()) + additionalLots" in bootstrap
    owner_update = function(manager, "bool StructureManager::updateStructureLotOwner(")
    assert "structure->getLotSize()" in owner_update
    transfer = (CORE / "src/server/zone/objects/creature/commands/TransferstructureCommand.h").read_text()
    assert "int lotSize = structure->getLotSize();" in transfer and "setAdditionalLots" not in transfer
    redeed = function(manager, "int StructureManager::redeedStructure(")
    assert "destroyStructure(structureObject)" in redeed and "setAdditionalLots" not in redeed
    task = (MANAGER / "tasks/DestroyStructureTask.h").read_text()
    assert "structureObject->destroyObjectFromDatabase(true)" in task
    place = function(manager, "StructureObject* StructureManager::placeStructure(")
    assert "reserveAccountLots(ghost, serverTemplate->getLotSize())" in place and "setAdditionalLots" not in place
    assert "additionalLots" not in (CORE / "src/server/zone/objects/tangible/deed/structure/StructureDeed.idl").read_text()
    print("11 persistence and lifecycle source-wiring checks passed")
    signatures = ["int StructureObjectImplementation::getBaseLotSize() const",
                  "int StructureObjectImplementation::getLotSize() const",
                  "bool StructureObjectImplementation::setAdditionalLots(",
                  "void StructureObjectImplementation::setOwner(",
                  "void StructureObjectImplementation::destroyObjectFromDatabase("]
    harness = HARNESS.replace("INITIALIZER", initializer.group(0))
    harness = harness.replace("MODEL_METHODS", "\n".join(function(source, item) for item in signatures))
    harness = harness.replace("RESIZE_METHOD", function(manager, "bool StructureManager::updateStructureLotCount("))
    with tempfile.TemporaryDirectory(prefix="structure-lot-model-", dir=CORE / "bin") as temporary:
        cpp = Path(temporary) / "model.cpp"
        binary = Path(temporary) / "model"
        cpp.write_text(harness)
        subprocess.run(shlex.split(os.environ.get("CXX", "g++")) + ["-std=c++11", "-pedantic-errors", "-Wall", "-Wextra", "-Werror",
                       "-fsanitize=undefined", "-fno-sanitize-recover=undefined", "-pthread", "-I", str(MANAGER), str(cpp), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
