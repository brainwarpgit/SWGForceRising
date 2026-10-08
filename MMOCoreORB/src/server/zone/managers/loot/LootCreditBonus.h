#ifndef LOOTCREDITBONUS_H_
#define LOOTCREDITBONUS_H_

#include "server/zone/objects/creature/CreatureObject.h"
#include <cmath>
#include <limits>

namespace LootCreditBonus {
	inline double expectedCredits(int level) {
		double cappedLevel = Math::max(0, level);
		double maxCredits = std::round((0.03 * cappedLevel * cappedLevel) + (3.0 * cappedLevel) + 50.0);
		double minCredits = std::round((maxCredits * 0.5) + (2.0 * cappedLevel));
		return (minCredits + maxCredits) * 0.5;
	}

	inline int apply(int baseCredits, int creatureLevel, CreatureObject* player) {
		if (baseCredits <= 0 || player == nullptr)
			return baseCredits;

		long long totalLuck = (long long)player->getSkillMod("luck") + player->getSkillMod("force_luck");
		long long maxLuck = (long long)std::numeric_limits<int>::max() - Math::max(0, creatureLevel);
		int luck = (int)(totalLuck < 0 ? 0 : (totalLuck > maxLuck ? maxLuck : totalLuck));
		if (luck == 0)
			return baseCredits;

		int levelBonus = System::random(luck);
		if (levelBonus == 0)
			return baseCredits;

		double baseExpected = expectedCredits(creatureLevel);
		double boostedExpected = expectedCredits(creatureLevel + levelBonus);
		double boostedCredits = std::round(baseCredits * (boostedExpected / baseExpected));
		return boostedCredits >= std::numeric_limits<int>::max() ? std::numeric_limits<int>::max() : (int)boostedCredits;
	}

	inline int applyGroup(int credits, int playerCount) {
		if (credits <= 0 || playerCount <= 1)
			return credits;

		// Each additional player adds 50% of the original creature-credit total.
		long long boosted = (long long)credits * (playerCount + 1) / 2;
		return boosted > std::numeric_limits<int>::max() ? std::numeric_limits<int>::max() : (int)boosted;
	}

	inline int applyAutoLoot(int credits, int bonusPercent) {
		if (credits <= 0 || bonusPercent <= 0)
			return credits;
		int cappedBonus = Math::min(15, bonusPercent);
		long long boosted = (long long)credits * (100 + cappedBonus) / 100;
		return boosted > std::numeric_limits<int>::max() ? std::numeric_limits<int>::max() : (int)boosted;
	}
}

#endif
