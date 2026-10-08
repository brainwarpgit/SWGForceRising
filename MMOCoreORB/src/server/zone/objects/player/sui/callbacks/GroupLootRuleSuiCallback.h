/*
 * GroupLootRuleSuiCallback.h
 *
 *  Created on: March 1, 2015
 *      Author: Anakis
 */

#ifndef GROUPLOOTRULESUICALLBACK_H_
#define GROUPLOOTRULESUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"

class GroupLootRuleSuiCallback : public SuiCallback {
public:
	GroupLootRuleSuiCallback(ZoneServer* server) : SuiCallback(server) {

	}

	void run(CreatureObject* player, SuiBox* suiBox, uint32 eventIndex, Vector<UnicodeString>* args) {
		bool cancelPressed = (eventIndex == 1);

		//Pre: player is locked
		//Post: player is locked

		if (cancelPressed || !suiBox->isListBox() || player == nullptr || args->size() <= 0)
			return;

		int selection = Integer::valueOf(args->get(0).toString()); //The row number they chose in the list.

		if (selection < 0 || selection > 4) //Player made no valid selection but pressed OK.
			return;

		ManagedReference<GroupObject*> group = player->getGroup();
		if (group == nullptr)
			return;

		Locker glocker(group, player);

		if (group->getLeader() != player)
			return;

		if (selection == 4) {
			bool enabled = !group->isAreaLootEnabled();
			group->setAreaLootEnabled(enabled);
			group->sendSystemMessage(enabled ? "Group Area Loot enabled." : "Group Area Loot disabled.");
			GroupManager::instance()->sendGroupLootMenu(player, group);
		} else {
			GroupManager::instance()->changeLootRule(group, selection);
		}
	}

};


#endif /* GROUPLOOTRULESUICALLBACK_H_ */
