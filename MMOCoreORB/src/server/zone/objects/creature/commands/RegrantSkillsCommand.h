/*
                Copyright <SWGEmu>
        See file COPYING for copying conditions.*/

#ifndef REGRANTSKILLSCOMMAND_H_
#define REGRANTSKILLSCOMMAND_H_

#include "server/zone/objects/player/sui/messagebox/SuiMessageBox.h"
#include "server/zone/objects/player/sui/callbacks/RegrantSkillsSuiCallback.h"

class RegrantSkillsCommand : public QueueCommand {
public:
	RegrantSkillsCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {
	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (creature == nullptr || !creature->isPlayerCreature())
			return GENERALERROR;
		if (!checkStateMask(creature))
			return INVALIDSTATE;
		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		PlayerObject* ghost = creature->getPlayerObject();
		if (ghost == nullptr)
			return GENERALERROR;
		if (!RegrantSkillsSuiCallback::checkCooldown(creature, ghost))
			return GENERALERROR;

		Reference<SuiMessageBox*> confirmation = new SuiMessageBox(creature, SuiWindowType::NONE);
		confirmation->setCallback(new RegrantSkillsSuiCallback(server->getZoneServer()));
		confirmation->setPromptTitle("Confirm Skill Refresh");
		confirmation->setPromptText(ghost->isAdmin()
			? "Refresh all of your learned skills using the server's current skill data? Your experience and progression will be preserved."
			: "Refresh all of your learned skills using the server's current skill data? Your experience and progression will be preserved. This can be done once every 12 hours.");
		confirmation->setCancelButton(true, "@no");
		confirmation->setOkButton(true, "@yes");
		ghost->addSuiBox(confirmation);
		creature->sendMessage(confirmation->generateMessage());
		return SUCCESS;
	}
};

#endif // REGRANTSKILLSCOMMAND_H_
