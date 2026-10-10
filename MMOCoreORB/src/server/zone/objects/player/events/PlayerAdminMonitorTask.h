#ifndef PLAYERADMINMONITORTASK_H_
#define PLAYERADMINMONITORTASK_H_

#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/player/sui/SuiWindowType.h"

class PlayerAdminMonitorTask : public Task {
	ManagedWeakReference<CreatureObject*> player;
	Coordinate initialPosition;

public:
	PlayerAdminMonitorTask(CreatureObject* creature) : Task() {
		player = creature;
		initialPosition.setPosition(creature->getPositionX(), creature->getPositionZ(), creature->getPositionY());
	}

	void run() {
		auto creature = player.get();
		if (creature == nullptr)
			return;

		Locker creatureLock(creature);
		PlayerObject* ghost = creature->getPlayerObject();
		if (ghost == nullptr) {
			creature->removePendingTask("player_admin_monitor");
			return;
		}

		if (!ghost->hasSuiBoxWindowType(SuiWindowType::PLAYER_ADMIN_SETTINGS)) {
			creature->removePendingTask("player_admin_monitor");
			return;
		}

		if (creature->isInCombat() || creature->getCurrentSpeed() > 0.f ||
				creature->getDistanceTo(&initialPosition) > 0.1f) {
			ghost->removeSuiBoxType(SuiWindowType::PLAYER_ADMIN_SETTINGS);
			creature->removePendingTask("player_admin_monitor");
			creature->sendSystemMessage("Player Settings closed because you moved or entered combat.");
			return;
		}

		reschedule(250);
	}
};

#endif
