#ifndef REGRANTSKILLSSUICALLBACK_H_
#define REGRANTSKILLSSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/messagebox/SuiMessageBox.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/managers/skill/SkillManager.h"

class RegrantSkillsSuiCallback : public SuiCallback {
public:
	static const int COOLDOWN_SECONDS = 12 * 60 * 60;

	RegrantSkillsSuiCallback(ZoneServer* server) : SuiCallback(server) {
	}

	static bool checkCooldown(CreatureObject* player, PlayerObject* ghost) {
		if (ghost->isAdmin())
			return true;

		String saved = ghost->getScreenPlayData("RegrantSkills", "nextUse");
		if (saved.isEmpty())
			return true;

		int64 remaining = Long::valueOf(saved) - static_cast<int64>(System::getTime());
		if (remaining <= 0)
			return true;

		int hours = static_cast<int>(remaining / 3600);
		int minutes = static_cast<int>((remaining % 3600 + 59) / 60);
		if (minutes == 60) {
			++hours;
			minutes = 0;
		}
		player->sendSystemMessage("You can refresh your skills again in " + String::valueOf(hours) + " hour(s) and " + String::valueOf(minutes) + " minute(s).");
		return false;
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isMessageBox() || eventIndex == 1 || server == nullptr)
			return;

		Locker locker(player);
		PlayerObject* ghost = player->getPlayerObject();
		if (ghost == nullptr || !checkCooldown(player, ghost))
			return;

		SkillManager* skillManager = SkillManager::instance();
		if (skillManager == nullptr || !skillManager->regrantSkills(player)) {
			player->sendSystemMessage("Could not refresh your skills. No skills were changed if a skill definition is missing.");
			return;
		}

		if (ghost->isAdmin()) {
			player->sendSystemMessage("Your skills have been refreshed from the server's current skill data.");
		} else {
			ghost->setScreenPlayData("RegrantSkills", "nextUse", String::valueOf(static_cast<int64>(System::getTime()) + COOLDOWN_SECONDS));
			player->sendSystemMessage("Your skills have been refreshed from the server's current skill data. You can use /regrantSkills again in 12 hours.");
		}
	}
};

#endif // REGRANTSKILLSSUICALLBACK_H_
