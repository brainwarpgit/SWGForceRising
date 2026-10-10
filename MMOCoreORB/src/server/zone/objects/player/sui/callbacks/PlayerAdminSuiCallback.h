#ifndef PLAYERADMINSUICALLBACK_H_
#define PLAYERADMINSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"
#include "server/zone/objects/player/sui/SuiWindowType.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/events/PlayerAdminMonitorTask.h"
#include "server/zone/ZoneServer.h"

class PlayerAdminSuiCallback : public SuiCallback {
	int menu;
	uint64 subjectID;

public:
	enum Menu { CATEGORIES, HARVESTING, LOOT, STRUCTURE };

	PlayerAdminSuiCallback(ZoneServer* server, int menu, uint64 subjectID) : SuiCallback(server), menu(menu), subjectID(subjectID) {}

	static void showMenu(CreatureObject* player, CreatureObject* subject, int menu) {
		if (player == nullptr || subject == nullptr || player->getPlayerObject() == nullptr || subject->getPlayerObject() == nullptr)
			return;
		if (subject != player && !player->getPlayerObject()->isAdmin())
			return;

		PlayerObject* ghost = subject->getPlayerObject();
		PlayerObject* playerGhost = player->getPlayerObject();
		playerGhost->removeSuiBoxType(SuiWindowType::PLAYER_ADMIN_SETTINGS);
		ManagedReference<SuiListBox*> box = new SuiListBox(player, SuiWindowType::PLAYER_ADMIN_SETTINGS);
		box->setCallback(new PlayerAdminSuiCallback(player->getZoneServer(), menu, subject->getObjectID()));
		box->setCancelButton(true, "@ui:cancel");
		box->setOkButton(true, "@ui:ok");
		String owner = subject == player ? "" : String(" - ") + subject->getFirstName();

		if (menu == CATEGORIES) {
			box->setPromptTitle(String("Player Settings") + owner);
			box->setPromptText("Choose a settings category.");
			box->addMenuItem("Harvesting");
			box->addMenuItem("Loot");
			box->addMenuItem("Structure");
		} else if (menu == STRUCTURE) {
			box->setPromptTitle(String("Structure Settings") + owner);
			box->setPromptText("Select a setting to toggle it.");
			box->addMenuItem(String("Destroy/Redeed Confirmation Code: ") +
					(ghost->isStructureDestroyCodeEnabled() ? "\\#32CD32Enabled\\#." : "\\#FF6347Disabled\\#."));
		} else if (menu == LOOT) {
			box->setPromptTitle(String("Loot Settings") + owner);
			box->setPromptText("Select a setting to toggle it. Area Loot applies to solo Loot All within 64 meters.");
			box->addMenuItem(String("Solo Area Loot: ") +
					(ghost->isAreaLootEnabled() ? "\\#32CD32Enabled\\#." : "\\#FF6347Disabled\\#."));
		} else if (menu == HARVESTING) {
			box->setPromptTitle(String("Harvesting Settings") + owner);
			box->setPromptText("Select a setting to toggle it. Area Harvest applies to eligible corpses within 64 meters.");
			box->addMenuItem(String("Area Harvest: ") +
					(ghost->isAreaHarvestEnabled() ? "\\#32CD32Enabled\\#." : "\\#FF6347Disabled\\#."));
		} else {
			return;
		}

		playerGhost->addSuiBox(box);
		player->sendMessage(box->generateMessage());
		if (player->getPendingTask("player_admin_monitor") == nullptr) {
			Reference<Task*> monitor = new PlayerAdminMonitorTask(player);
			player->addPendingTask("player_admin_monitor", monitor, 250);
		}
	}

	void run(CreatureObject* player, SuiBox* box, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || box == nullptr || !box->isListBox() || eventIndex == 1 ||
				args == nullptr || args->size() < 1)
			return;
		if (player->isInCombat() || player->getCurrentSpeed() > 0.f) {
			player->getPlayerObject()->removeSuiBoxType(SuiWindowType::PLAYER_ADMIN_SETTINGS);
			player->sendSystemMessage("Player Settings closed because you moved or entered combat.");
			return;
		}

		String selectionText = args->get(0).toString();
		if (selectionText != "0" && selectionText != "1" && selectionText != "2")
			return;
		ManagedReference<CreatureObject*> subject = player->getZoneServer()->getObject(subjectID).castTo<CreatureObject*>();
		if (subject == nullptr || !subject->isPlayerCreature() || subject->getPlayerObject() == nullptr) {
			player->sendSystemMessage("That player is no longer available.");
			return;
		}
		if (subject != player && (player->getPlayerObject() == nullptr || !player->getPlayerObject()->isAdmin())) {
			player->sendSystemMessage("Only admins can change another player's settings.");
			return;
		}

		if (menu == CATEGORIES) {
			showMenu(player, subject, selectionText == "0" ? HARVESTING : selectionText == "1" ? LOOT : STRUCTURE);
		} else if ((menu == STRUCTURE || menu == LOOT || menu == HARVESTING) && selectionText == "0") {
			PlayerObject* ghost = subject->getPlayerObject();
			if (ghost == nullptr)
				return;
			if (player->isInCombat() || player->getCurrentSpeed() > 0.f) {
				player->sendSystemMessage("You must be out of combat and stationary to change player settings.");
				return;
			}
			bool enabled;
			{
				Locker ghostLocker(ghost, player);
				if (menu == STRUCTURE) {
					enabled = !ghost->isStructureDestroyCodeEnabled();
					ghost->setStructureDestroyCodeEnabled(enabled);
				} else if (menu == LOOT) {
					enabled = !ghost->isAreaLootEnabled();
					ghost->setAreaLootEnabled(enabled);
				} else {
					enabled = !ghost->isAreaHarvestEnabled();
					ghost->setAreaHarvestEnabled(enabled);
				}
				ghost->updateToDatabase();
			}
			String prefix = subject == player ? String("") : subject->getFirstName() + String(": ");
			if (menu == STRUCTURE)
				player->sendSystemMessage(prefix + (enabled ?
						"Destroy/redeed confirmation code enabled." :
						"Destroy/redeed confirmation code disabled. The Yes/No confirmation and other structure checks still apply."));
			else if (menu == LOOT)
				player->sendSystemMessage(prefix + (enabled ? "Solo Area Loot enabled." : "Solo Area Loot disabled."));
			else
				player->sendSystemMessage(prefix + (enabled ? "Area Harvest enabled." : "Area Harvest disabled."));
			showMenu(player, subject, menu);
		}
	}
};

#endif // PLAYERADMINSUICALLBACK_H_
