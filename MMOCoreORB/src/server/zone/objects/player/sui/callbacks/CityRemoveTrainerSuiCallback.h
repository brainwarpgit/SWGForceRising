#ifndef CITYREMOVETRAINERSUICALLBACK_H_
#define CITYREMOVETRAINERSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/scene/SceneObject.h"

class CityRemoveTrainerSuiCallback : public SuiCallback {
	ManagedWeakReference<CityRegion*> cityRegion;
	uint64 trainerID;

public:
	CityRemoveTrainerSuiCallback(ZoneServer* server, CityRegion* city, uint64 objectID)
			: SuiCallback(server), trainerID(objectID) {
		cityRegion = city;
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isMessageBox() || eventIndex != 0)
			return;

		auto city = cityRegion.get();
		auto ghost = player->getPlayerObject();
		if (city == nullptr || ghost == nullptr || (!city->isMayor(player->getObjectID()) && !ghost->isAdmin()))
			return;

		Locker cityLock(city, player);
		auto trainer = server->getObject(trainerID);
		if (trainer == nullptr || !city->isCitySkillTrainer(trainer)) {
			player->sendSystemMessage("That trainer is no longer registered with this city.");
			return;
		}

		Locker trainerLock(trainer, city);
		city->removeSkillTrainers(trainer);
		trainer->destroyObjectFromWorld(true);
		trainer->destroyObjectFromDatabase(true);
		player->sendSystemMessage("City trainer removed.");
	}
};

#endif
