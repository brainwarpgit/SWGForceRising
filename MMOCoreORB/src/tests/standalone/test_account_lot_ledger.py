#!/usr/bin/env python3
"""Test the scalar account-lot ledger with an isolated standard-library harness.

Uses strict C++11 to check the header's compatibility with the server build.
Compiles only AccountLotLedger.h and this harness, without Core3, engine3,
database access, or game objects. Temporary files stay under MMOCoreORB/bin.
Real persistence bootstrap, placement, transfers, and UI need integration tests.
"""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile


CORE = Path(__file__).resolve().parents[3]
HEADER = CORE / "src/server/zone/managers/structure/AccountLotLedger.h"

HARNESS = r'''
#include "AccountLotLedger.h"
#include <atomic>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <thread>
#include <vector>

int checks = 0;
void check(bool result, const char* description) {
    if (!result) {
        std::cerr << "FAIL: " << description << '\n';
        std::exit(1);
    }
    ++checks;
}

void ownershipAndCapacity() {
    AccountLotLedger ledger;
    check(!ledger.isReady(), "ledger starts unavailable");
    check(ledger.remaining(1, 100) == 0, "unavailable ledger grants no capacity");
    check(ledger.reserve(1, 100, 1) == 0, "unavailable ledger rejects reservations");
    check(!ledger.registerOwner(0, 1), "zero owner is invalid");
    check(!ledger.registerOwner(11, 0), "zero account is invalid");
    check(ledger.registerOwner(11, 1), "register first character");
    check(ledger.registerOwner(12, 1), "register offline sibling character");
    check(ledger.registerOwner(21, 2), "register other account");
    check(ledger.registerOwner(11, 1), "repeat owner registration is idempotent");
    check(!ledger.registerOwner(11, 2), "owner cannot silently move accounts");
    check(!ledger.setStructure(100, 99, 2), "unknown owner is rejected");
    check(!ledger.setStructure(0, 11, 2), "zero structure is rejected");
    check(!ledger.setStructure(100, 11, -1), "negative structure cost is rejected");
    check(ledger.setStructure(100, 11, 2), "bootstrap is allowed before ready");
    check(ledger.setStructure(101, 12, 5), "offline sibling ownership is represented");
    check(ledger.setStructure(200, 21, 9), "other account ownership is represented");
    ledger.setReady(true);
    check(ledger.isReady(), "bootstrap may make ledger ready");
    check(ledger.remaining(1, 100) == 93, "account includes both characters");
    check(ledger.remaining(2, 100) == 91, "account balances are isolated");
    check(ledger.setStructure(100, 11, 2), "same structure record can be refreshed");
    check(ledger.remaining(1, 100) == 93, "duplicate records do not duplicate cost");
    check(ledger.remaining(1, 300) == 293, "capacity is not limited to a byte");
    auto large = ledger.reserve(1, 300, 290);
    check(large != 0 && ledger.remaining(1, 300) == 3,
          "reservations above 255 retain their full cost");
    ledger.release(large);
    check(ledger.remaining(1, 5) == 0, "reduced capacity clamps remaining at zero");
    check(ledger.remaining(1, -100) == 0, "negative capacity grants no lots");
    check(ledger.remaining(0, 100) == 0, "invalid account grants no lots");
    check(ledger.reserve(0, 100, 1) == 0, "invalid account cannot reserve");
    check(ledger.reserve(1, 100, -1) == 0, "negative reservation cannot reserve");
    check(ledger.reserve(1, 100, 1, 999) == 0, "unknown transfer source cannot reserve");
    check(ledger.setStructure(100, 21, 2), "authoritative owner change moves usage");
    check(ledger.remaining(1, 100) == 95 && ledger.remaining(2, 100) == 89,
          "owner change debits only the recipient account");
    ledger.removeStructure(101);
    ledger.removeStructure(101);
    check(ledger.remaining(1, 100) == 100, "removal is idempotent");
    check(ledger.setStructure(300, 11, INT_MAX), "maximum integer cost can be stored");
    check(ledger.setStructure(301, 12, INT_MAX), "multiple huge costs can be stored");
    check(ledger.remaining(1, INT_MAX) == 0, "large usage cannot wrap into credit");
}

void reservations() {
    AccountLotLedger ledger;
    ledger.registerOwner(11, 1);
    ledger.registerOwner(21, 2);
    ledger.setReady(true);
    auto token = ledger.reserve(1, 100, 80);
    check(token != 0, "placement reserves lots");
    check(ledger.remaining(1, 100) == 20, "pending placement is charged immediately");
    check(ledger.reserve(1, 100, 21) == 0, "reservation prevents overspending");
    check(!ledger.setStructure(100, 11, 81, token), "commit cannot exceed reserved lots");
    check(!ledger.setStructure(100, 21, 80, token), "commit cannot use another account's token");
    check(!ledger.setStructure(100, 99, 80, token), "commit cannot use unknown owner");
    check(ledger.remaining(1, 100) == 20, "failed commit preserves the reservation");
    check(ledger.setStructure(100, 11, 75, token), "smaller final cost can commit");
    check(ledger.remaining(1, 100) == 25, "commit replaces reservation with actual cost");
    check(!ledger.setStructure(101, 11, 1, token), "committed token cannot be reused");
    ledger.release(token);
    check(ledger.remaining(1, 100) == 25, "release after commit has no effect");
    auto cancelled = ledger.reserve(1, 100, 25);
    check(cancelled != 0 && ledger.remaining(1, 100) == 0, "remaining capacity may be reserved");
    ledger.release(cancelled);
    ledger.release(cancelled);
    ledger.release(0);
    check(ledger.remaining(1, 100) == 25, "cancellation restores capacity once");
    check(!ledger.setStructure(101, 11, 25, cancelled), "cancelled token cannot commit");
    auto zero = ledger.reserve(1, 0, 0);
    check(zero != 0, "zero-cost placement works when over capacity");
    check(ledger.setStructure(102, 11, 0, zero), "zero-cost reservation can commit");
    auto unavailable = ledger.reserve(1, 100, 20);
    ledger.setReady(false);
    check(ledger.remaining(1, 100) == 0, "unavailable transition fails closed");
    check(!ledger.setStructure(103, 11, 20, unavailable), "unavailable ledger rejects prior token");
    ledger.setReady(true);
    check(ledger.remaining(1, 100) == 25, "ready reset preserves ownership but drops reservations");
    check(!ledger.setStructure(103, 11, 20, unavailable), "old token stays invalid after recovery");
}

void transfers() {
    AccountLotLedger ledger;
    ledger.registerOwner(11, 1);
    ledger.registerOwner(12, 1);
    ledger.registerOwner(21, 2);
    ledger.registerOwner(31, 3);
    ledger.setStructure(100, 11, 10);
    ledger.setStructure(200, 21, 5);
    ledger.setReady(true);
    auto internal = ledger.reserve(1, 10, 10, 100);
    check(internal != 0, "full account may transfer between its characters");
    check(ledger.remaining(1, 10) == 0, "internal transfer consumes no extra lots");
    check(ledger.reserve(1, 10, 10, 100) == 0, "same structure cannot reserve twice");
    check(ledger.reserve(3, 100, 10, 100) == 0, "transfer contention spans accounts");
    check(!ledger.setStructure(101, 12, 10, internal), "transfer token is tied to its structure");
    check(!ledger.setStructure(100, 12, 11, internal), "zero-charge transfer still checks full reserved size");
    check(ledger.setStructure(100, 12, 10, internal), "full-cost structure commits zero-charge transfer");
    check(ledger.remaining(1, 10) == 0, "internal transfer leaves account total unchanged");
    auto overCap = ledger.reserve(1, 5, 10, 100);
    check(overCap != 0, "internal transfer works after capacity is reduced");
    ledger.release(overCap);
    check(ledger.reserve(2, 14, 10, 100) == 0, "cross-account transfer requires recipient space");
    auto cross = ledger.reserve(2, 15, 10, 100);
    check(cross != 0, "recipient can reserve exact remaining space");
    check(ledger.remaining(1, 15) == 5 && ledger.remaining(2, 15) == 0,
          "source keeps ownership while recipient reserves");
    check(ledger.setStructure(100, 12, 10), "identical ownership refresh succeeds during transfer");
    check(ledger.remaining(2, 15) == 0, "identical ownership refresh preserves recipient reservation");
    check(ledger.reserve(3, 100, 10, 100) == 0, "identical refresh preserves transfer exclusivity");
    check(!ledger.setStructure(100, 31, 10, cross), "transfer cannot change reserved recipient account");
    check(ledger.setStructure(100, 21, 10, cross), "cross-account transfer commits atomically");
    check(ledger.remaining(1, 15) == 15 && ledger.remaining(2, 15) == 0,
          "successful transfer refunds source and consumes reservation");
    auto destroyed = ledger.reserve(1, 15, 10, 100);
    check(destroyed != 0, "existing structure can be reserved again after commit");
    ledger.removeStructure(100);
    check(ledger.remaining(1, 15) == 15, "destruction cancels pending recipient charge");
    check(!ledger.setStructure(100, 11, 10, destroyed), "removed structure cannot be resurrected by stale token");
    check(ledger.remaining(2, 15) == 10, "destruction removes old owner usage");
    ledger.setStructure(100, 11, 10);
    auto superseded = ledger.reserve(2, 15, 10, 100);
    check(superseded != 0, "transfer can be queued before admin ownership change");
    check(ledger.setStructure(100, 31, 10), "admin ownership change can supersede transfer");
    check(!ledger.setStructure(100, 21, 10, superseded), "superseded transfer cannot overwrite new ownership");
    check(ledger.remaining(2, 15) == 10 && ledger.remaining(3, 15) == 5,
          "superseded reservation releases recipient charge");
    auto resized = ledger.reserve(2, 15, 10, 100);
    check(resized != 0, "transfer can be queued before an authoritative cost change");
    check(ledger.setStructure(100, 31, 9), "real cost change succeeds without changing owner");
    check(ledger.remaining(2, 15) == 10 && ledger.remaining(3, 15) == 6,
          "real cost change supersedes the queued transfer and updates usage");
    check(!ledger.setStructure(100, 21, 10, resized), "cost change invalidates stale transfer token");
}

void concurrentSpending() {
    AccountLotLedger ledger;
    ledger.registerOwner(11, 1);
    ledger.registerOwner(12, 1);
    ledger.setReady(true);
    constexpr int contenders = 16;
    std::atomic<int> ready{0};
    std::atomic<bool> start{false};
    std::vector<AccountLotLedger::ID> results(contenders);
    std::vector<std::thread> threads;
    for (int i = 0; i < contenders; ++i) {
        threads.emplace_back([&, i] {
            ready.fetch_add(1);
            while (!start.load()) std::this_thread::yield();
            results[i] = ledger.reserve(1, 10, 6);
        });
    }
    while (ready.load() != contenders) std::this_thread::yield();
    start.store(true);
    for (auto& thread : threads) thread.join();
    int winners = 0;
    AccountLotLedger::ID winner = 0;
    for (auto result : results) {
        if (result != 0) { ++winners; winner = result; }
    }
    check(winners == 1, "simultaneous account spending admits only one winner");
    check(ledger.remaining(1, 10) == 4, "concurrent reservation balance is exact");
    check(ledger.setStructure(100, 12, 6, winner), "winning sibling character can commit");
    check(ledger.remaining(1, 10) == 4, "concurrent winner commit preserves balance");
}

void resizing() {
    AccountLotLedger ledger;
    ledger.registerOwner(11, 1);
    ledger.registerOwner(12, 1);
    ledger.registerOwner(21, 2);
    ledger.setStructure(100, 11, 5);
    ledger.setStructure(101, 12, 2);
    ledger.setStructure(200, 21, 9);
    check(!ledger.canResizeStructure(100, 11, 5), "unready ledger hides resizing capability");
    check(!ledger.resizeStructure(100, 11, 5, 4, 10), "unready ledger rejects even shrinking");
    ledger.setReady(true);
    struct Invalid { AccountLotLedger::ID structure, owner; int expected; };
    for (const auto& value : std::vector<Invalid>{
            {0, 11, 5}, {100, 0, 5}, {999, 11, 5}, {100, 99, 5},
            {100, 12, 5}, {100, 21, 5}, {100, 11, 4}, {100, 11, -1}, {100, 11, INT_MIN}}) {
        check(!ledger.canResizeStructure(value.structure, value.owner, value.expected),
              "unknown, zero, stale owner or stale cost cannot offer resizing");
        check(!ledger.resizeStructure(value.structure, value.owner, value.expected, 6, 10),
              "resize atomically rejects inconsistent identity or cost");
    }
    check(!ledger.resizeStructure(100, 11, 5, -1, 10), "negative new cost rejected");
    check(!ledger.resizeStructure(100, 11, 5, INT_MIN, 10), "minimum integer new cost rejected before arithmetic");
    check(ledger.remaining(1, 10) == 3, "rejected resizes preserve all account usage");
    check(ledger.canResizeStructure(100, 11, 5), "matching record offers resizing");
    check(ledger.resizeStructure(100, 11, 5, 7, 10), "growth charges positive difference only");
    check(ledger.remaining(1, 10) == 1 && ledger.remaining(2, 10) == 1, "growth updates owning account alone");
    check(!ledger.canResizeStructure(100, 11, 5) && !ledger.resizeStructure(100, 11, 5, 8, 10),
          "stale expected cost cannot spend again");
    auto placement = ledger.reserve(1, 10, 1);
    check(placement != 0 && !ledger.resizeStructure(100, 11, 7, 8, 10), "pending placement prevents double spending capacity");
    check(ledger.canResizeStructure(100, 11, 7), "capacity exhaustion does not invalidate the structure record");
    ledger.release(placement);
    auto otherAccount = ledger.reserve(2, 10, 1);
    check(otherAccount != 0 && ledger.resizeStructure(100, 11, 7, 8, 10), "other account reservation does not block growth");
    check(!ledger.resizeStructure(100, 11, 8, 9, 10), "full account rejects further growth");
    check(ledger.resizeStructure(100, 11, 8, 8, 0), "unchanged cost succeeds without capacity");
    check(ledger.resizeStructure(100, 11, 8, 7, 1), "over-capacity account may shrink");
    check(ledger.remaining(1, 1) == 0, "partial shrink does not fabricate remaining capacity");
    check(ledger.resizeStructure(100, 11, 7, 0, -10), "scalar ledger allows nonnegative shrink with negative capacity");
    check(ledger.remaining(1, 10) == 8, "shrink releases actual usage");
    auto transfer = ledger.reserve(2, 10, 0, 100);
    check(transfer != 0 && !ledger.canResizeStructure(100, 11, 0), "pending transfer hides resizing capability");
    check(!ledger.resizeStructure(100, 11, 0, 1, 10), "pending transfer blocks resize without cancelling transfer");
    check(ledger.setStructure(100, 21, 0, transfer), "blocked resize leaves transfer token usable");
    check(!ledger.canResizeStructure(100, 11, 0) && ledger.canResizeStructure(100, 21, 0),
          "completed transfer changes permitted title owner");
    ledger.setStructure(100, 21, 1);
    auto internal = ledger.reserve(2, 0, 1, 100);
    check(internal != 0 && !ledger.resizeStructure(100, 21, 1, 0, 0), "same-account pending transfer also blocks shrinking");
    ledger.release(internal);
    check(ledger.canResizeStructure(100, 21, 1) && ledger.resizeStructure(100, 21, 1, 0, 0),
          "cancelled transfer restores capability and permits shrinking");
    ledger.removeStructure(100);
    check(!ledger.canResizeStructure(100, 21, 0) && !ledger.resizeStructure(100, 21, 0, 1, 10),
          "removed structure cannot be recreated through resizing");
}

void resizeLimitsAndTransferGrowth() {
    AccountLotLedger ledger;
    ledger.registerOwner(11, 1);
    ledger.registerOwner(12, 1);
    ledger.setStructure(100, 11, 5);
    ledger.setReady(true);
    check(ledger.reserve(1, 5, 6, 100) == 0, "same-account transfer cannot grow cost in a full pool");
    auto growth = ledger.reserve(1, 10, 9, 100);
    check(growth != 0 && ledger.remaining(1, 10) == 1, "existing same-account reservation charges growth difference");
    check(ledger.reserve(1, 10, 2) == 0, "reserved transfer growth blocks competing placement");
    check(!ledger.setStructure(100, 12, 10, growth), "transfer commit cannot grow beyond reserved final cost");
    check(ledger.setStructure(100, 12, 9, growth) && ledger.remaining(1, 10) == 1,
          "same-account growth commit replaces charged difference without double billing");
    auto shrink = ledger.reserve(1, 0, 6, 100);
    check(shrink != 0 && ledger.setStructure(100, 11, 6, shrink), "same-account shrinking transfer needs no free lots");
    check(ledger.remaining(1, 10) == 4, "shrinking transfer releases correct difference");
    ledger.setStructure(100, 11, INT_MAX - 1);
    check(ledger.resizeStructure(100, 11, INT_MAX - 1, INT_MAX, INT_MAX), "growth reaches maximum integer cost without overflow");
    check(ledger.remaining(1, INT_MAX) == 0, "maximum cost consumes exact capacity");
    check(ledger.resizeStructure(100, 11, INT_MAX, 0, INT_MIN), "extreme shrink is safe even below zero capacity");
    auto placement = ledger.reserve(1, INT_MAX, 1);
    check(placement != 0 && !ledger.resizeStructure(100, 11, 0, INT_MAX, INT_MAX), "maximum growth still respects other reservations");
    ledger.release(placement);
    check(ledger.resizeStructure(100, 11, 0, INT_MAX, INT_MAX), "full integer-range growth succeeds with sufficient capacity");
    ledger.setStructure(101, 12, INT_MAX);
    check(ledger.resizeStructure(100, 11, INT_MAX, INT_MAX - 1, INT_MAX), "huge aggregate usage still permits shrinking");
    check(!ledger.resizeStructure(100, 11, INT_MAX - 1, INT_MAX, INT_MAX), "huge aggregate usage cannot wrap and fund growth");
}

void concurrentResizing() {
    AccountLotLedger ledger;
    ledger.registerOwner(11, 1);
    ledger.registerOwner(12, 1);
    ledger.setStructure(100, 11, 2);
    ledger.setStructure(101, 12, 2);
    ledger.setReady(true);
    std::atomic<int> ready{0}, winners{0};
    std::atomic<bool> start{false};
    std::vector<std::thread> threads;
    for (int i = 0; i < 16; ++i) {
        threads.emplace_back([&, i] {
            ready.fetch_add(1);
            while (!start.load()) std::this_thread::yield();
            if (ledger.resizeStructure(100 + i % 2, 11 + i % 2, 2, 3, 5)) winners.fetch_add(1);
        });
    }
    while (ready.load() != 16) std::this_thread::yield();
    start.store(true);
    for (auto& thread : threads) thread.join();
    check(winners.load() == 1 && ledger.remaining(1, 5) == 0, "concurrent sibling storage additions admit one funded change");
    check(ledger.canResizeStructure(100, 11, 3) != ledger.canResizeStructure(101, 12, 3),
          "only one concurrent structure cost changes");

    AccountLotLedger mixed;
    mixed.registerOwner(11, 1);
    mixed.setStructure(100, 11, 4);
    mixed.setReady(true);
    ready.store(0); start.store(false);
    AccountLotLedger::ID token = 0;
    bool resized = false;
    std::thread placement([&] {
        ready.fetch_add(1);
        while (!start.load()) std::this_thread::yield();
        token = mixed.reserve(1, 5, 1);
    });
    std::thread resize([&] {
        ready.fetch_add(1);
        while (!start.load()) std::this_thread::yield();
        resized = mixed.resizeStructure(100, 11, 4, 5, 5);
    });
    while (ready.load() != 2) std::this_thread::yield();
    start.store(true);
    placement.join(); resize.join();
    check((token != 0) != resized, "placement and resizing atomically compete for the same remaining lot");
    check(mixed.remaining(1, 5) == 0, "mixed concurrent allocation cannot overspend");
    mixed.release(token);
    check(mixed.remaining(1, 5) == (resized ? 0 : 1), "cancelling competing placement preserves any committed resize");
}

int main() {
    ownershipAndCapacity();
    reservations();
    transfers();
    concurrentSpending();
    resizing();
    resizeLimitsAndTransferGrowth();
    concurrentResizing();
    std::cout << "PASS: " << checks << " account lot ledger checks\n";
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix="account-lots-", dir=CORE / "bin") as work:
        directory = Path(work)
        source = directory / "ledger_test.cpp"
        executable = directory / "ledger_test"
        source.write_text(HARNESS)
        compiler = shlex.split(os.environ.get("CXX", "c++"))
        subprocess.run(
            compiler + ["-std=c++11", "-pedantic-errors", "-O2", "-pthread", "-Wall", "-Wextra", "-Werror",
                        "-I", str(HEADER.parent), str(source), "-o", str(executable)],
            check=True, timeout=60,
        )
        subprocess.run([str(executable)], check=True, timeout=20)


if __name__ == "__main__":
    main()
