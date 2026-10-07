#ifndef PLAYERADMINSUICALLBACK_H_
#define PLAYERADMINSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"
#include "server/zone/objects/player/sui/SuiWindowType.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/ZoneServer.h"

class PlayerAdminSuiCallback : public SuiCallback {
	int menu;
	uint64 subjectID;

public:
	enum Menu { CATEGORIES, STORAGE };

	PlayerAdminSuiCallback(ZoneServer* server, int menu, uint64 subjectID) : SuiCallback(server), menu(menu), subjectID(subjectID) {}

	static void showMenu(CreatureObject* player, CreatureObject* subject, int menu) {
		if (player == nullptr || subject == nullptr || player->getPlayerObject() == nullptr || subject->getPlayerObject() == nullptr)
			return;
		if (subject != player && !player->getPlayerObject()->isAdmin())
			return;

		PlayerObject* ghost = subject->getPlayerObject();
		ManagedReference<SuiListBox*> box = new SuiListBox(player, SuiWindowType::NONE);
		box->setCallback(new PlayerAdminSuiCallback(player->getZoneServer(), menu, subject->getObjectID()));
		box->setCancelButton(true, "@ui:cancel");
		box->setOkButton(true, "@ui:ok");
		String owner = subject == player ? "" : String(" - ") + subject->getFirstName();

		if (menu == CATEGORIES) {
			box->setPromptTitle(String("Player Settings") + owner);
			box->setPromptText("Choose a settings category.");
			box->addMenuItem("Storage");
		} else if (menu == STORAGE) {
			box->setPromptTitle(String("Storage Settings") + owner);
			box->setPromptText("Select a setting to toggle it.");
			box->addMenuItem(String("Destroy/Redeed Confirmation Code: ") +
					(ghost->isStructureDestroyCodeEnabled() ? "\\#32CD32Enabled\\#." : "\\#FF6347Disabled\\#."));
		} else {
			return;
		}

		player->getPlayerObject()->addSuiBox(box);
		player->sendMessage(box->generateMessage());
	}

	void run(CreatureObject* player, SuiBox* box, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || box == nullptr || !box->isListBox() || eventIndex == 1 ||
				args == nullptr || args->size() < 1)
			return;

		String selectionText = args->get(0).toString();
		if (selectionText != "0")
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
			showMenu(player, subject, STORAGE);
		} else if (menu == STORAGE) {
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
				enabled = !ghost->isStructureDestroyCodeEnabled();
				ghost->setStructureDestroyCodeEnabled(enabled);
				ghost->updateToDatabase();
			}
			player->sendSystemMessage((subject == player ? String("") : subject->getFirstName() + String(": ")) + (enabled ?
					"Destroy/redeed confirmation code enabled." :
					"Destroy/redeed confirmation code disabled. The Yes/No confirmation and other structure checks still apply."));
			showMenu(player, subject, STORAGE);
		}
	}
};

#endif // PLAYERADMINSUICALLBACK_H_
