/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#include "InformantMissionScreenHandler.h"
#include "server/zone/objects/mission/BountyMissionObjective.h"

const String InformantMissionScreenHandler::STARTSCREENHANDLERID = "convoscreenstart";

MissionObject* InformantMissionScreenHandler::getBountyMissionObject(CreatureObject* player) {
	if (player == nullptr) {
		return nullptr;
	}

	SceneObject* datapad = player->getSlottedObject("datapad");

	if (datapad == nullptr) {
		return nullptr;
	}

	int datapadSize = datapad->getContainerObjectsSize();

	for (int i = 0; i < datapadSize; ++i) {
		if (datapad->getContainerObject(i)->isMissionObject()) {
			Reference<MissionObject*> mission = datapad->getContainerObject(i).castTo<MissionObject*>();

			if (mission != nullptr && mission->getTypeCRC() == MissionTypes::BOUNTY) {
				BountyMissionObjective* objective = cast<BountyMissionObjective*>(mission->getMissionObjective());
				if (objective != nullptr) {
					return mission;
				}
			}
		}
	}

	//No relevant mission found.
	return nullptr;
}

ConversationScreen* InformantMissionScreenHandler::handleScreen(CreatureObject* conversingPlayer, SceneObject* conversingNPC, int selectedOption, ConversationScreen* conversationScreen) {
	//Check if player is bounty hunter.
	if (!conversingPlayer->hasSkill("combat_bountyhunter_novice")) {
		conversationScreen->setDialogText(String("@mission/mission_generic:informant_not_bounty_hunter"));
	} else {
		//Get bounty mission object if it exists.
		MissionObject* mission = getBountyMissionObject(conversingPlayer);

		if (mission == nullptr) {
			//Player has no bounty mission.
			conversationScreen->setDialogText(String("@mission/mission_generic:informant_no_bounty_mission"));
		} else {
			//Any SpyNet informant can provide the information for the active bounty mission.
			BountyMissionObjective* objective = cast<BountyMissionObjective*>(mission->getMissionObjective());
			if (objective != nullptr) {
				//Run mission logic.
				if (objective->getObjectiveStatus() == BountyMissionObjective::INITSTATUS) {
					objective->updateMissionStatus(mission->getMissionLevel());
					if (objective->getObjectiveStatus() == BountyMissionObjective::HASBIOSIGNATURESTATUS) {
						//Player received info about target position.
						int randomStringValue = System::random(4) + 1;
						conversationScreen->setDialogText("@mission/mission_bounty_informant:target_easy_" + String::valueOf(randomStringValue));
					} else {
						//Should never happen.
						error("Bounty mission update failed.");
					}
				} else {
					//Player has already got the target position.
					conversationScreen->setDialogText(String("@mission/mission_generic:informant_no_bounty_mission"));
				}
			} else {
				//Player has already got the target position.
				conversationScreen->setDialogText(String("@mission/mission_generic:informant_no_bounty_mission"));
			}
		}
	}
	return conversationScreen;
}
