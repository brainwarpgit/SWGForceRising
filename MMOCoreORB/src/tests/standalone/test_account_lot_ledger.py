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

int main() {
    ownershipAndCapacity();
    reservations();
    transfers();
    concurrentSpending();
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
