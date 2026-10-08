/*
 * GroupLootCommand.h
 *
 *  Modified on: March 2, 2015
 *      Author: Anakis
 */

#ifndef GROUPLOOTCOMMAND_H_
#define GROUPLOOTCOMMAND_H_

#include "server/zone/objects/group/GroupObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/managers/group/GroupManager.h"

class GroupLootCommand : public QueueCommand {
public:

	GroupLootCommand(const String& name, ZoneProcessServer* server)
		: QueueCommand(name, server) {

	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {

		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		ManagedReference<PlayerObject*> ghost = creature->getPlayerObject();
		if (ghost == nullptr)
			return GENERALERROR;

		//Check if player is in a group.
		ManagedReference<GroupObject*> group = creature->getGroup();
		if (group == nullptr) {
			StringIdChatParameter groupOnly("group", "group_only"); //"You can only set or check group looting options if you are in a group."
			creature->sendSystemMessage(groupOnly);
			return GENERALERROR;
		}

		Locker glocker(group, creature);

		//Check if player is the group leader. If not, give current loot rule and stop.
		if (group->getLeader() != creature) {
			StringIdChatParameter error;

			switch (group->getLootRule()) {
			case GroupManager::FREEFORALL:
				error.setStringId("group","selected_free4all"); //"Group Leader selected Free For All as the loot type for the group."
				break;
			case GroupManager::MASTERLOOTER:
				error.setStringId("group","selected_master"); //"Group Leader selected Master Looter as the loot type for the group."
				break;
			case GroupManager::LOTTERY:
				error.setStringId("group","selected_lotto"); //"Group Leader selected Lottery as the loot type for the group."
				break;
			case GroupManager::RANDOM:
				error.setStringId("group","selected_random"); //"Group Leader selected Random as the loot type for the group."
				break;
			default:
				return GENERALERROR;
			}

			creature->sendSystemMessage(error);
			String areaStatus = group->isAreaLootEnabled() ? "Enabled" : "Disabled";
			if (group->getLootRule() == GroupManager::MASTERLOOTER)
				areaStatus += " (inactive with Master Looter)";
			creature->sendSystemMessage(String("Group Area Loot: ") + areaStatus + ".");
			return GENERALERROR;
		}

		GroupManager::instance()->sendGroupLootMenu(creature, group);

		return SUCCESS;

	}

};

#endif /* GROUPLOOTCOMMAND_H_ */
