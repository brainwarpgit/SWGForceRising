#ifndef PLAYERADMINCOMMAND_H_
#define PLAYERADMINCOMMAND_H_

#include "server/zone/objects/player/sui/callbacks/PlayerAdminSuiCallback.h"
#include "server/zone/managers/player/PlayerManager.h"
#include "server/zone/ZoneServer.h"

class PlayerAdminCommand : public QueueCommand {
public:
	PlayerAdminCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (creature == nullptr || !creature->isPlayerCreature() || creature->getPlayerObject() == nullptr)
			return GENERALERROR;
		if (!checkStateMask(creature))
			return INVALIDSTATE;
		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;
		if (creature->isInCombat() || creature->getCurrentSpeed() > 0.f) {
			creature->sendSystemMessage("You must be out of combat and stationary to use player settings.");
			return INVALIDSTATE;
		}

		ManagedReference<CreatureObject*> subject = creature;
		String name = arguments.toString().trim();
		uint64 selectedID = target != 0 ? target : creature->getTargetID();
		if (!name.isEmpty() || (creature->getPlayerObject()->isAdmin() && selectedID != 0 && selectedID != creature->getObjectID())) {
			if (!creature->getPlayerObject()->isAdmin()) {
				creature->sendSystemMessage("Only admins can change another player's settings.");
				return INSUFFICIENTPERMISSION;
			}
			if (!name.isEmpty())
				subject = server->getZoneServer()->getPlayerManager()->getPlayer(name);
			else
				subject = server->getZoneServer()->getObject(selectedID).castTo<CreatureObject*>();
			if (subject == nullptr || !subject->isPlayerCreature() || subject->getPlayerObject() == nullptr) {
				creature->sendSystemMessage("That player must be online to change their settings.");
				return INVALIDTARGET;
			}
		}

		PlayerAdminSuiCallback::showMenu(creature, subject, PlayerAdminSuiCallback::CATEGORIES);
		return SUCCESS;
	}
};

#endif // PLAYERADMINCOMMAND_H_
