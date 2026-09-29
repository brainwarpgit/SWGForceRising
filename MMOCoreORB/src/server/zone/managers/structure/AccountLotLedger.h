/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef ACCOUNTLOTLEDGER_H_
#define ACCOUNTLOTLEDGER_H_

#include <algorithm>
#include <cstdint>
#include <mutex>
#include <unordered_map>

// Derived ownership records and reservations only. Callers supply persisted
// owners/structures; no game objects or callbacks are accessed under this mutex.
class AccountLotLedger {
public:
	using ID = std::uint64_t;
	using AccountID = std::uint32_t;

	bool registerOwner(ID owner, AccountID account) {
		if (owner == 0 || account == 0)
			return false;

		std::lock_guard<std::mutex> lock(mutex);
		auto entry = owners.emplace(owner, account);
		return entry.second || entry.first->second == account;
	}

	void setReady(bool value) {
		std::lock_guard<std::mutex> lock(mutex);
		ready = value;

		if (!ready) {
			reservations.clear();
			reservedStructures.clear();
		}
	}

	bool isReady() const {
		std::lock_guard<std::mutex> lock(mutex);
		return ready;
	}

	bool belongsToAccount(ID owner, AccountID account) const {
		std::lock_guard<std::mutex> lock(mutex);
		auto entry = owners.find(owner);
		return ready && account != 0 && entry != owners.end() && entry->second == account;
	}

	bool setStructure(ID structure, ID owner, int lots, ID reservation = 0) {
		if (structure == 0 || lots < 0)
			return false;

		std::lock_guard<std::mutex> lock(mutex);
		auto ownerEntry = owners.find(owner);

		if (ownerEntry == owners.end())
			return false;

		if (reservation == 0) {
			auto existing = structures.find(structure);
			if (existing != structures.end() && existing->second.owner == owner
					&& existing->second.account == ownerEntry->second && existing->second.lots == lots)
				return true; // An unchanged ownership refresh must not cancel a queued transfer.
		}

		if (reservation != 0) {
			auto pending = reservations.find(reservation);

			if (!ready || pending == reservations.end()
					|| pending->second.account != ownerEntry->second
					|| lots > pending->second.expectedLots
					|| (pending->second.structure != 0 && pending->second.structure != structure))
				return false;

			auto other = reservedStructures.find(structure);

			if (other != reservedStructures.end() && other->second != reservation)
				return false;
		}

		structures[structure] = StructureRecord{owner, ownerEntry->second, lots};

		// An authoritative bootstrap/admin change supersedes a queued transfer.
		auto old = reservedStructures.find(structure);
		if (old != reservedStructures.end())
			releaseLocked(old->second);

		if (reservation != 0)
			releaseLocked(reservation);

		return true;
	}

	void removeStructure(ID structure) {
		std::lock_guard<std::mutex> lock(mutex);
		structures.erase(structure);

		auto pending = reservedStructures.find(structure);
		if (pending != reservedStructures.end())
			releaseLocked(pending->second);
	}

	int remaining(AccountID account, int capacity) const {
		std::lock_guard<std::mutex> lock(mutex);
		return ready && account != 0 ? remainingLocked(account, capacity) : 0;
	}

	ID reserve(AccountID account, int capacity, int lots, ID existingStructure = 0) {
		if (account == 0 || lots < 0)
			return 0;

		std::lock_guard<std::mutex> lock(mutex);
		if (!ready)
			return 0;

		int chargedLots = lots;

		if (existingStructure != 0) {
			auto existing = structures.find(existingStructure);

			if (existing == structures.end() || reservedStructures.count(existingStructure) != 0)
				return 0;

			if (existing->second.account == account)
				chargedLots = 0;
		}

		if (chargedLots > remainingLocked(account, capacity))
			return 0;

		ID id;
		do {
			id = nextReservation++;
		} while (id == 0 || reservations.count(id) != 0);

		reservations.emplace(id, PendingReservation{account, lots, chargedLots, existingStructure});

		if (existingStructure != 0)
			reservedStructures.emplace(existingStructure, id);

		return id;
	}

	void release(ID reservation) {
		std::lock_guard<std::mutex> lock(mutex);
		releaseLocked(reservation);
	}

private:
	struct StructureRecord {
		ID owner;
		AccountID account;
		int lots;
	};

	struct PendingReservation {
		AccountID account;
		int expectedLots;
		int chargedLots;
		ID structure;
	};

	int remainingLocked(AccountID account, int capacity) const {
		std::int64_t available = std::max(0, capacity);

		// Saturate at zero while subtracting, so even very large accounts cannot
		// wrap a total and accidentally gain capacity. All stored costs are >= 0.
		for (const auto& entry : structures) {
			if (entry.second.account == account)
				available = std::max<std::int64_t>(0, available - entry.second.lots);
		}

		for (const auto& entry : reservations) {
			if (entry.second.account == account)
				available = std::max<std::int64_t>(0, available - entry.second.chargedLots);
		}

		return static_cast<int>(available);
	}

	void releaseLocked(ID reservation) {
		auto pending = reservations.find(reservation);
		if (pending == reservations.end())
			return;

		if (pending->second.structure != 0)
			reservedStructures.erase(pending->second.structure);

		reservations.erase(pending);
	}

	mutable std::mutex mutex;
	bool ready = false;
	ID nextReservation = 1;
	std::unordered_map<ID, AccountID> owners;
	std::unordered_map<ID, StructureRecord> structures;
	std::unordered_map<ID, PendingReservation> reservations;
	std::unordered_map<ID, ID> reservedStructures;
};

#endif // ACCOUNTLOTLEDGER_H_
