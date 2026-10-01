#ifndef CITYCLEARTRAINERSSUICALLBACK_H_
#define CITYCLEARTRAINERSSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/scene/SceneObject.h"

using namespace server::zone::objects::region;
using namespace server::zone::objects::creature;

class CityClearTrainersSuiCallback : public SuiCallback {
	ManagedWeakReference<CityRegion*> cityRegion;
	Vector<uint64> trainerIDs;

public:
	CityClearTrainersSuiCallback(ZoneServer* server, CityRegion* city, const Vector<uint64>& trainers)
			: SuiCallback(server), trainerIDs(trainers) {
		cityRegion = city;
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || !sui->isMessageBox() || eventIndex == 1)
			return;

		auto city = cityRegion.get();
		auto ghost = player->getPlayerObject();
		if (city == nullptr || ghost == nullptr || (!city->isMayor(player->getObjectID()) && !ghost->isAdmin()))
			return;

		Locker cityLock(city, player);
		int removed = 0;
		for (int i = 0; i < trainerIDs.size(); ++i) {
			auto trainer = server->getObject(trainerIDs.get(i));
			if (trainer == nullptr || !city->isCitySkillTrainer(trainer))
				continue;

			Locker trainerLock(trainer, city);
			city->removeSkillTrainers(trainer);
			trainer->destroyObjectFromWorld(true);
			trainer->destroyObjectFromDatabase(true);
			++removed;
		}
		player->sendSystemMessage(String::valueOf(removed) + " city trainer(s) removed.");
	}
};

#endif
