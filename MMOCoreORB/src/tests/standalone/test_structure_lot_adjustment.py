#!/usr/bin/env python3
"""Exercise production storage-lot UI/service methods with the real scalar ledger.

Only extracted methods, the standalone ledger header, and standard-library
mocks are compiled. Model persistence, game-object locks, and client dialogs
still require Core3/in-game validation. No Core3 or engine3 build is performed.
"""

import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]


def function(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


MOCKS = r'''
#include "server/zone/managers/structure/AccountLotLedger.h"
#include <cassert>
#include <cctype>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
using uint64 = std::uint64_t;
using uint32 = std::uint32_t;
using int64 = std::int64_t;
struct String: std::string {
    using std::string::string;
    String() {}
    String(const std::string& value): std::string(value) {}
    int length() const { return static_cast<int>(size()); }
    bool isEmpty() const { return empty(); }
    char charAt(int index) const { return at(index); }
    String toString() const { return *this; }
    String trim() const {
        std::size_t first = 0, end = size();
        while (first < end && std::isspace(static_cast<unsigned char>(at(first)))) ++first;
        while (end > first && std::isspace(static_cast<unsigned char>(at(end - 1)))) --end;
        return substr(first, end - first);
    }
    static String valueOf(int value) { return std::to_string(value); }
};
using UnicodeString = String;
template<class T> struct Vector: std::vector<T> {
    using std::vector<T>::vector;
    const T& get(int index) const { return this->at(index); }
};
struct StringBuffer {
    std::ostringstream out;
    template<class T> StringBuffer& operator<<(const T& value) { out << value; return *this; }
    String toString() const { return out.str(); }
};
template<class T> struct Ref {
    T value;
    Ref(T value = nullptr): value(value) {}
    T get() const { return value; }
    T operator->() const { return value; }
    operator T() const { return value; }
};
template<class T> using ManagedReference = Ref<T>;
template<class T, class U> T cast(U* value) { return static_cast<T>(value); }
struct Zone {};
struct ZoneServer {};
struct SceneObject {
    uint64 id = 0;
    int lockDepth = 0;
    virtual ~SceneObject() {}
    virtual bool isStructureObject() const { return false; }
    uint64 getObjectID() const { return id; }
};
struct SuiTransferBox;
struct PlayerObject {
    uint32 accountID;
    int capacity = 100;
    bool online = true, staff = false;
    std::vector<std::shared_ptr<SuiTransferBox>> boxes;
    explicit PlayerObject(uint32 account): accountID(account) {}
    uint32 getAccountID() const { return accountID; }
    bool isOnline() const { return online; }
    void addSuiBox(SuiTransferBox* box);
};
struct CreatureObject: SceneObject {
    PlayerObject* ghost;
    Zone* zone;
    SceneObject* root = nullptr;
    bool player = true;
    int sent = 0;
    std::vector<String> messages;
    CreatureObject(uint64 id, PlayerObject* ghost, Zone* zone): ghost(ghost), zone(zone) { this->id = id; }
    bool isPlayerCreature() const { return player; }
    PlayerObject* getPlayerObject() const { return ghost; }
    Zone* getZone() const { return zone; }
    SceneObject* getRootParent() const { return root; }
    ZoneServer* getZoneServer() const { static ZoneServer server; return &server; }
    void sendSystemMessage(const String& message) { messages.push_back(message); }
    void sendMessage(void*) { ++sent; }
};
struct ConfigManager {
    int itemsPerLot = 200;
    static ConfigManager* instance() { static ConfigManager manager; return &manager; }
    int getInt(const String& key, int) const {
        assert(key == "Core3.StructureManager.ItemsPerLot");
        return itemsPerLot;
    }
};
struct StructureObject: SceneObject {
    uint64 ownerID = 11;
    int base = 2, extra = 3, used = 0;
    bool building = true, pending = false, staticBuilding = false, explicitAdmin = false;
    Zone* zone;
    explicit StructureObject(Zone* zone): zone(zone) { id = 100; }
    bool isStructureObject() const override { return true; }
    bool isBuildingObject() const { return building; }
    bool isStaticBuilding() const { return staticBuilding; }
    bool isPendingDestruction() const { return pending; }
    Zone* getZone() const { return zone; }
    uint64 getOwnerObjectID() const { return ownerID; }
    int getBaseLotSize() const { return base; }
    int getAdditionalLots() const { return extra; }
    int getLotSize() const { return base + extra; }
    int getCurrentNumberOfPlayerItems() const { return used; }
    int getMaximumNumberOfPlayerItems() const {
        const int rate = ConfigManager::instance()->itemsPerLot;
        const int64 amount = static_cast<int64>(getLotSize()) * (rate > 0 ? rate : 0);
        return amount > std::numeric_limits<int>::max() ? std::numeric_limits<int>::max() : static_cast<int>(amount);
    }
    bool isOwnedByAccount(CreatureObject* player) const;
    bool setAdditionalLots(int value, int capacity);
};
using BuildingObject = StructureObject;
struct Locker {
    SceneObject* object;
    Locker(SceneObject* object, CreatureObject*): object(object) { ++object->lockDepth; }
    ~Locker() { --object->lockDepth; }
};
struct StructureManager {
    AccountLotLedger accountLots;
    std::function<void()> beforeCapacityRead;
    static StructureManager* current;
    static StructureManager* instance() { return current; }
    bool isAccountLotsReady() const { return accountLots.isReady(); }
    int getAccountLotsRemaining(PlayerObject* ghost) const {
        return accountLots.remaining(ghost->getAccountID(), ghost->capacity);
    }
    int getMaximumAccountLots(PlayerObject* ghost) {
        if (beforeCapacityRead) { auto hook = beforeCapacityRead; beforeCapacityRead = nullptr; hook(); }
        return ghost->capacity;
    }
    int getStorageLotAdjustmentLimit(CreatureObject*, StructureObject*, bool);
    void promptStructureLotAdjustment(CreatureObject*, StructureObject*, bool);
    bool applyStructureLotAdjustment(CreatureObject*, StructureObject*, bool, int, uint64, int);
};
StructureManager* StructureManager::current = nullptr;
bool StructureObject::isOwnedByAccount(CreatureObject* player) const {
    return player && player->isPlayerCreature() && ownerID != 0 &&
        (ownerID == player->getObjectID() || (player->ghost &&
        StructureManager::instance()->accountLots.belongsToAccount(ownerID, player->ghost->getAccountID())));
}
bool StructureObject::setAdditionalLots(int value, int capacity) {
    assert(lockDepth > 0);
    if (!StructureManager::instance()->accountLots.resizeStructure(id, ownerID, getLotSize(), base + value, capacity)) return false;
    extra = value;
    return true;
}
struct SuiBox {
    bool transfer = true;
    SceneObject* object = nullptr;
    virtual ~SuiBox() {}
    bool isTransferBox() const { return transfer; }
    Ref<SceneObject*> getUsingObject() const { return object; }
};
struct SuiCallback {
    explicit SuiCallback(ZoneServer*) {}
    virtual ~SuiCallback() {}
    virtual void run(CreatureObject*, SuiBox*, uint32, Vector<UnicodeString>*) = 0;
};
CALLBACK_CLASS
struct SuiTransferBox: SuiBox {
    String title, text, from, to, fromAmount, toAmount;
    bool cancel = false;
    std::unique_ptr<SuiCallback> callback;
    SuiTransferBox(CreatureObject*, uint32) {}
    void setUsingObject(SceneObject* value) { object = value; }
    void setCallback(SuiCallback* value) { callback.reset(value); }
    void setPromptTitle(const String& value) { title = value; }
    void setPromptText(const String& value) { text = value; }
    void setCancelButton(bool value, const String&) { cancel = value; }
    void addFrom(const String& label, const String& start, const String& input, const String&) {
        from = label; fromAmount = start; assert(start == input);
    }
    void addTo(const String& label, const String& start, const String& input, const String&) {
        to = label; toAmount = start; assert(start == input);
    }
    void* generateMessage() { return this; }
};
void PlayerObject::addSuiBox(SuiTransferBox* box) { boxes.emplace_back(box); }
SERVICE_METHODS
int checks = 0;
void check(bool passed, const char* description) {
    ++checks;
    if (!passed) { std::cerr << "FAIL: " << description << '\n'; std::exit(1); }
}
struct Fixture {
    Zone zone, elsewhere;
    StructureManager manager;
    BuildingObject building{&zone};
    PlayerObject ownerGhost{1}, altGhost{1}, otherGhost{2};
    CreatureObject owner{11, &ownerGhost, &zone}, alt{12, &altGhost, &zone}, other{21, &otherGhost, &zone};
    Fixture() {
        StructureManager::current = &manager;
        ConfigManager::instance()->itemsPerLot = 200;
        manager.accountLots.registerOwner(11, 1);
        manager.accountLots.registerOwner(12, 1);
        manager.accountLots.registerOwner(21, 2);
        manager.accountLots.setStructure(100, 11, 5);
        manager.accountLots.setReady(true);
        owner.root = alt.root = other.root = &building;
    }
    void setLots(int base, int extra) {
        building.base = base;
        building.extra = extra;
        manager.accountLots.setStructure(100, building.ownerID, building.getLotSize());
    }
    int limit(bool remove = false) { return manager.getStorageLotAdjustmentLimit(&alt, &building, remove); }
    bool apply(int amount, bool remove = false) {
        return manager.applyStructureLotAdjustment(&alt, &building, remove, amount, building.ownerID, building.extra);
    }
    void callback(const String& input, bool remove = false, uint32 event = 0) {
        SuiBox box;
        box.object = &building;
        StructureLotAdjustmentSuiCallback callback(alt.getZoneServer(), building.ownerID, building.extra, remove);
        Vector<UnicodeString> args{"from-slider-value", input};
        callback.run(&alt, &box, event, &args);
    }
};
void eligibility() {
    { Fixture f;
      check(f.limit() == 1 && f.limit(true) == 3, "same-account alt can add or remove eligible lots");
      check(f.manager.getStorageLotAdjustmentLimit(&f.owner, &f.building, false) == 1, "title owner retains adjustment access");
      f.building.explicitAdmin = true;
      check(f.manager.getStorageLotAdjustmentLimit(&f.other, &f.building, false) == 0, "unrelated explicit admin receives no owner-account adjustment rights");
      f.otherGhost.staff = true;
      check(f.manager.getStorageLotAdjustmentLimit(&f.other, &f.building, false) == 0, "staff status cannot bypass owner-account restriction"); }
    const std::vector<std::function<void(Fixture&)>> invalid = {
        [](Fixture& f) { f.alt.player = false; },
        [](Fixture& f) { f.alt.ghost = nullptr; },
        [](Fixture& f) { f.altGhost.online = false; },
        [](Fixture& f) { f.altGhost.accountID = 0; },
        [](Fixture& f) { f.alt.root = nullptr; },
        [](Fixture& f) { f.alt.zone = &f.elsewhere; },
        [](Fixture& f) { f.building.zone = nullptr; },
        [](Fixture& f) { f.building.pending = true; },
        [](Fixture& f) { f.building.building = false; },
        [](Fixture& f) { f.building.staticBuilding = true; },
        [](Fixture& f) { f.setLots(0, 0); },
        [](Fixture& f) { f.building.extra = -1; },
        [](Fixture& f) { f.manager.accountLots.setReady(false); },
        [](Fixture& f) { f.manager.accountLots.removeStructure(100); },
        [](Fixture& f) { f.manager.accountLots.setStructure(100, 11, 6); },
        [](Fixture& f) { f.manager.accountLots.reserve(1, 100, 5, 100); },
    };
    for (const auto& invalidate: invalid) {
        Fixture f; invalidate(f);
        check(f.limit() == 0 && f.limit(true) == 0, "ineligible or changing structure cannot expose adjustment limits");
        const int extra = f.building.extra;
        check(!f.apply(1) && f.building.extra == extra, "ineligible adjustment does not mutate saved extra lots");
    }
    { Fixture f;
      check(f.manager.getStorageLotAdjustmentLimit(nullptr, &f.building, false) == 0, "null player has no adjustment limit");
      check(f.manager.getStorageLotAdjustmentLimit(&f.alt, nullptr, false) == 0, "null structure has no adjustment limit"); }
}
void limitsAndChanges() {
    { Fixture f;
      f.setLots(2, 0);
      f.manager.accountLots.setStructure(101, 12, 96);
      check(f.limit() == 2, "all sibling-owned structures consume the shared allowance");
      auto reservation = f.manager.accountLots.reserve(1, 100, 1);
      check(reservation != 0 && f.limit() == 1, "queued allocations also reduce available extra lots");
      check(!f.apply(2) && f.building.extra == 0, "addition cannot overspend reserved account lots");
      check(f.apply(1) && f.building.extra == 1 && f.limit() == 0, "exact available addition succeeds and charges the account");
      f.manager.accountLots.release(reservation);
      check(f.limit() == 1, "released unrelated reservation restores only its own charge"); }
    { Fixture f;
      f.altGhost.capacity = std::numeric_limits<int>::max();
      f.setLots(200, 399);
      check(f.limit() == 1, "structure cap has one remaining added lot");
      check(f.apply(1) && f.building.getLotSize() == 600, "last permitted structure lot can be added safely");
      check(f.limit() == 0 && !f.apply(1), "twice-base cap blocks further additions"); }
    { Fixture f;
      f.setLots(2, 5);
      check(f.limit() == 0 && f.limit(true) == 5, "older over-cap allocation can be reduced but never expanded");
      check(f.apply(1, true) && f.building.extra == 4 && f.limit() == 0,
            "removing an over-cap allocation restores the new maximum without refunding base lots"); }
    { Fixture f;
      struct Removal { int used, allowed; };
      for (const Removal item: {Removal{0, 3}, Removal{400, 3}, Removal{401, 2}, Removal{600, 2}, Removal{601, 1}, Removal{800, 1}, Removal{801, 0}, Removal{1000, 0}, Removal{1001, 0}, Removal{-1, 0}}) {
          f.building.used = item.used;
          check(f.limit(true) == item.allowed, "removal retains base lots and ceiling of used storage");
      }
      f.building.used = 401;
      check(!f.apply(3, true) && f.building.extra == 3, "removal cannot put existing contents over capacity");
      check(f.apply(2, true) && f.building.extra == 1, "largest safe removal succeeds");
      check(f.manager.accountLots.remaining(1, 100) == 97 && f.building.getMaximumNumberOfPlayerItems() == 600,
            "removal refunds account lots and lowers storage consistently");
      f.building.used = 0;
      check(f.apply(1, true) && f.building.extra == 0 && f.building.getLotSize() == 2, "all added lots can be removed but base cost remains");
      check(f.limit(true) == 0 && !f.apply(1, true), "base lots are never removable"); }
    for (int rate: {0, -1, std::numeric_limits<int>::min()}) {
        Fixture f; ConfigManager::instance()->itemsPerLot = rate;
        check(f.limit(true) == 3, "empty building may refund added lots when storage rate is nonpositive");
        f.building.used = 1;
        check(f.limit(true) == 0, "occupied building cannot remove storage at nonpositive item rate");
    }
    { Fixture f;
      ConfigManager::instance()->itemsPerLot = std::numeric_limits<int>::max();
      f.building.used = std::numeric_limits<int>::max();
      check(f.limit(true) == 3, "ceiling arithmetic for huge storage values does not overflow");
      f.altGhost.capacity = 1;
      check(f.limit() == 0 && f.apply(3, true), "over-capacity account can still refund extra lots"); }
    { Fixture f;
      f.manager.beforeCapacityRead = [&]() { f.manager.accountLots.reserve(1, 100, 5, 100); };
      check(!f.apply(1) && f.building.extra == 3, "ledger reservation between limit check and write rejects without mutating extras");
      check(f.manager.accountLots.remaining(1, 100) == 95, "failed resize leaves the old account charge intact"); }
    { Fixture f;
      const int extra = f.building.extra;
      check(!f.apply(0) && !f.apply(-1) && f.building.extra == extra, "service rejects nonpositive direct-call amounts");
      check(!f.manager.applyStructureLotAdjustment(&f.alt, &f.building, false, 1, 21, extra), "stale owner snapshot is rejected");
      check(!f.manager.applyStructureLotAdjustment(&f.alt, &f.building, false, 1, 11, extra - 1), "stale extra-lot snapshot is rejected");
      check(f.building.extra == extra && f.building.lockDepth == 0, "rejected snapshots preserve contents and release service lock"); }
}
void dialogs() {
    { Fixture f;
      f.setLots(2, 1);
      f.manager.promptStructureLotAdjustment(&f.alt, &f.building, false);
      check(f.altGhost.boxes.size() == 1 && f.alt.sent == 1, "eligible alt receives a slider dialog");
      auto box = f.altGhost.boxes.back();
      check(box->title == "Add Storage Lots" && box->object == &f.building, "add dialog identifies action and structure");
      check(box->cancel && box->fromAmount == "3" && box->toAmount == "0", "slider permits cancel and shows the allowed range");
      check(box->text.find("Base: 2") != String::npos && box->text.find("added: 1 / 4") != String::npos
            && box->text.find("Storage:") != String::npos, "slider explains current lots and storage");
      Vector<UnicodeString> args{"99999", "2"};
      box->callback->run(&f.alt, box.get(), 0, &args);
      check(f.building.extra == 3 && f.manager.accountLots.remaining(1, 100) == 95, "slider's second field is validated independently of its displayed source balance");
      box->callback->run(&f.alt, box.get(), 0, &args);
      check(f.building.extra == 3, "replayed dialog cannot repeat a completed purchase");
      f.manager.promptStructureLotAdjustment(&f.alt, &f.building, true);
      check(f.altGhost.boxes.back()->title == "Remove Storage Lots" && f.altGhost.boxes.back()->fromAmount == "3", "remove action gets its own slider"); }
    { Fixture f;
      f.alt.root = nullptr;
      f.manager.promptStructureLotAdjustment(&f.alt, &f.building, false);
      check(f.altGhost.boxes.empty() && f.alt.sent == 0 && !f.alt.messages.empty(), "ineligible prompt explains rejection without creating a dialog"); }
    for (const String& input: {String("1"), String(" 2 "), String("0002")}) {
        Fixture f; f.setLots(2, 0); f.callback(input);
        check(f.building.extra > 0, "trimmed positive whole-number slider value is accepted");
    }
    for (const String& input: {String(), String(" "), String("0"), String("-1"), String("+1"), String("1.0"), String("1e2"), String("1 2"), String("2text"), String("2147483648"), String("9999999999"), String("00000000001")}) {
        Fixture f; f.callback(input);
        check(f.building.extra == 3 && f.alt.messages.size() == 1, "malformed or overflowing input rejects without mutation");
    }
    for (uint32 event: {1u, 2u}) {
        Fixture f; f.callback("2", false, event);
        check(f.building.extra == 3 && f.alt.messages.empty(), "cancel/non-OK event leaves structure untouched");
    }
    { Fixture f;
      SuiBox box; box.object = &f.building;
      StructureLotAdjustmentSuiCallback callback(f.alt.getZoneServer(), 11, 3, false);
      Vector<UnicodeString> args{"0", "1"}, empty;
      callback.run(&f.alt, &box, 0, nullptr);
      callback.run(&f.alt, &box, 0, &empty);
      check(f.building.extra == 3 && f.alt.messages.size() == 2, "missing input vectors are rejected safely");
      callback.run(nullptr, &box, 0, &args);
      callback.run(&f.alt, nullptr, 0, &args);
      box.transfer = false;
      callback.run(&f.alt, &box, 0, &args);
      check(f.building.extra == 3 && f.alt.messages.size() == 2, "null and non-transfer callback context is ignored");
      box.transfer = true; box.object = nullptr;
      callback.run(&f.alt, &box, 0, &args);
      SceneObject unrelated; box.object = &unrelated;
      callback.run(&f.alt, &box, 0, &args);
      check(f.building.extra == 3 && f.alt.messages.size() == 4, "missing or non-structure dialog object cannot be adjusted"); }
    { Fixture f;
      f.manager.promptStructureLotAdjustment(&f.alt, &f.building, false);
      auto box = f.altGhost.boxes.back();
      f.building.ownerID = 21;
      f.manager.accountLots.setStructure(100, 21, 5);
      Vector<UnicodeString> args{"0", "1"};
      box->callback->run(&f.alt, box.get(), 0, &args);
      check(f.building.extra == 3 && f.manager.accountLots.remaining(2, 100) == 95, "stale dialog cannot alter a transferred structure or its new account balance"); }
    { Fixture f;
      f.manager.promptStructureLotAdjustment(&f.alt, &f.building, true);
      auto box = f.altGhost.boxes.back();
      f.building.used = 801;
      Vector<UnicodeString> args{"0", "1"};
      box->callback->run(&f.alt, box.get(), 0, &args);
      check(f.building.extra == 3, "items inserted after opening removal dialog prevent unsafe reduction"); }
}
int main() {
    eligibility();
    limitsAndChanges();
    dialogs();
    std::cout << checks << " structure lot service and callback checks passed\n";
}
'''


def main():
    manager = (CORE / "src/server/zone/managers/structure/StructureManager.cpp").read_text()
    callback = (CORE / "src/server/zone/objects/player/sui/callbacks/StructureLotAdjustmentSuiCallback.h").read_text()
    radial = (CORE / "src/server/zone/objects/tangible/terminal/components/StructureTerminalMenuComponent.cpp").read_text()
    menu = function(radial, "void addStorageLotMenus(")
    assert 'getStorageLotAdjustmentLimit(player, structure, false)' in menu and '118, 241, 3, "Add Storage Lots"' in menu
    assert 'getStorageLotAdjustmentLimit(player, structure, true)' in menu and '118, 242, 3, "Remove Storage Lots"' in menu
    handler = function(radial, "int StructureTerminalMenuComponent::handleObjectMenuSelect(")
    assert re.search(r'if \(selectedID == 241 \|\| selectedID == 242\).*?promptStructureLotAdjustment\(creature, structureObject, selectedID == 242\)', handler, re.S)
    report = function(manager, "void StructureManager::reportStructureStatus(")
    assert 'getLotSize()' in report and 'getBaseLotSize()' in report and 'getAdditionalLots()' in report
    assert 'getMaximumNumberOfPlayerItems()' in report
    print("5 storage lot radial/report source checks passed", flush=True)
    source = MOCKS.replace("CALLBACK_CLASS", function(callback, "class StructureLotAdjustmentSuiCallback") + ";")
    methods = "\n".join(function(manager, signature) for signature in (
        "int StructureManager::getStorageLotAdjustmentLimit(",
        "void StructureManager::promptStructureLotAdjustment(",
        "bool StructureManager::applyStructureLotAdjustment(",
    ))
    source = source.replace("SERVICE_METHODS", methods)
    with tempfile.TemporaryDirectory(prefix=".structure-lot-adjustment-", dir=CORE / "bin") as directory:
        directory = Path(directory)
        cpp, executable = directory / "test.cpp", directory / "test"
        cpp.write_text(source)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(compiler + ["-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic-errors", "-pthread",
                                   "-fsanitize=undefined", "-fno-sanitize-recover=undefined", "-I", str(CORE / "src"),
                                   str(cpp), "-o", str(executable)], check=True, timeout=60)
        subprocess.run([str(executable)], check=True, timeout=20)


if __name__ == "__main__":
    main()
