#ifndef CITYTRAINERRENAMESUICALLBACK_H_
#define CITYTRAINERRENAMESUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/managers/name/NameManager.h"
#include "server/zone/managers/stringid/StringIdManager.h"
#include "server/zone/ZoneProcessServer.h"

class CityTrainerRenameSuiCallback : public SuiCallback {
public:
	CityTrainerRenameSuiCallback(ZoneServer* server) : SuiCallback(server) {}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isInputBox() || eventIndex == 1 || args == nullptr || args->size() < 1)
			return;

		ManagedReference<SceneObject*> trainer = sui->getUsingObject().get();
		if (trainer == nullptr || !trainer->isCreatureObject() || !trainer->isInRange(player, 20))
			return;

		ManagedReference<SceneObject*> root = trainer->getRootParent();
		ManagedReference<CityRegion*> city = nullptr;
		if (root != nullptr && root->isBuildingObject())
			city = root->getCityRegion().get();
		if (city == nullptr)
			city = trainer->getCityRegion().get();

		PlayerObject* ghost = player->getPlayerObject();
		if (city == nullptr || ghost == nullptr || (!city->hasMayorAuthority(player) && !ghost->isAdmin()))
			return;

		String role = StringIdManager::instance()->getStringId(trainer->getObjectName()->getFullPath().hashCode()).toString();
		if (role.isEmpty())
			return;

		String name = args->get(0).toString().trim();
		String suffix = " (" + role + ")";
		if (name.endsWith(suffix))
			name = name.subString(0, name.length() - suffix.length()).trim();
		if (name.isEmpty() || name.length() > 64) {
			player->sendSystemMessage("Enter a personal name of 1 to 64 characters.");
			return;
		}

		ZoneProcessServer* processServer = player->getZoneProcessServer();
		NameManager* nameManager = processServer != nullptr ? processServer->getNameManager() : nullptr;
		if (nameManager == nullptr || nameManager->checkNamingFilter(name) != NameManagerResult::ACCEPTED) {
			player->sendSystemMessage("That name is not allowed.");
			return;
		}

		Locker cityLock(city, player);
		if (!city->isCitySkillTrainer(trainer))
			return;
		Locker trainerLock(trainer, city);
		String displayName = name + suffix;
		trainer->setCustomObjectName(displayName, true);
		player->sendSystemMessage("City NPC renamed to " + displayName + ".");
	}
};

#endif
