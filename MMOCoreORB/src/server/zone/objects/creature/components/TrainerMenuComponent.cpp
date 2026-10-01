/*
 * TrainerMenuComponent.cpp
 *
 *  Created on: 4/28/2012
 *      Author: TragD
 */

#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "TrainerMenuComponent.h"
#include "server/zone/packets/object/ObjectMenuResponse.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/managers/city/CityRemoveAmenityTask.h"
#include "server/zone/objects/player/sui/inputbox/SuiInputBox.h"
#include "server/zone/objects/player/sui/callbacks/CityTrainerRenameSuiCallback.h"

namespace {
ManagedReference<CityRegion*> getRecruitedTrainerCity(SceneObject* trainer) {
	ManagedReference<CityRegion*> city = nullptr;
	ManagedReference<SceneObject*> root = trainer->getRootParent();
	if (root != nullptr && root->isBuildingObject())
		city = root->getCityRegion().get();
	if (city == nullptr)
		city = trainer->getCityRegion().get();
	return city;
}
}

void TrainerMenuComponent::fillObjectMenuResponse(SceneObject* sceneObject, ObjectMenuResponse* menuResponse, CreatureObject* player) const {
	TangibleObjectMenuComponent::fillObjectMenuResponse(sceneObject, menuResponse, player);

	ManagedReference<CityRegion*> city = getRecruitedTrainerCity(sceneObject);

	PlayerObject* ghost = player->getPlayerObject();
	if (city != nullptr && ghost != nullptr && (city->isMayor(player->getObjectID()) || ghost->isAdmin()) && city->isCitySkillTrainer(sceneObject)) {
		menuResponse->addRadialMenuItem(249, 3, "Rename City NPC");
		menuResponse->addRadialMenuItem(72, 3, "@city/city:mt_remove"); // Remove
	}
}

int TrainerMenuComponent::handleObjectMenuSelect(SceneObject* sceneObject, CreatureObject* player, byte selectedID) const {
	if (selectedID == 249) {
		ManagedReference<CityRegion*> city = getRecruitedTrainerCity(sceneObject);
		PlayerObject* ghost = player->getPlayerObject();
		if (city == nullptr || ghost == nullptr || (!city->isMayor(player->getObjectID()) && !ghost->isAdmin()) ||
				!city->isCitySkillTrainer(sceneObject) || !sceneObject->isInRange(player, 20))
			return 0;

		ManagedReference<SuiInputBox*> box = new SuiInputBox(player, 0);
		box->setUsingObject(sceneObject);
		box->setPromptTitle("Rename City NPC");
		box->setPromptText("Enter a new personal name. The NPC's role will be kept automatically. Current name: " + sceneObject->getDisplayedName());
		box->setMaxInputSize(64);
		box->setForceCloseDistance(20);
		box->setCallback(new CityTrainerRenameSuiCallback(player->getZoneServer()));
		ghost->addSuiBox(box);
		player->sendMessage(box->generateMessage());
		return 0;
	}

	if (selectedID == 72) {
		ManagedReference<CityRegion*> city = getRecruitedTrainerCity(sceneObject);

		PlayerObject* ghost = player->getPlayerObject();
		if (city != nullptr && ghost != nullptr && (city->isMayor(player->getObjectID()) || ghost->isAdmin()) && city->isCitySkillTrainer(sceneObject)) {
			CityRemoveAmenityTask* task = new CityRemoveAmenityTask(sceneObject, city);
			task->execute();

			player->sendSystemMessage("@city/city:mt_removed"); // The object has been removed from the city.

		}

		return 0;

	}

	return TangibleObjectMenuComponent::handleObjectMenuSelect(sceneObject, player, selectedID);
}
