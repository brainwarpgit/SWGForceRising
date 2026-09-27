/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef REVOKESKILLCOMMAND_H_
#define REVOKESKILLCOMMAND_H_

#include "server/zone/managers/skill/SkillManager.h"

class RevokeSkillCommand : public QueueCommand {
public:
	RevokeSkillCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {
		setCharacterAbility("admin");
	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (creature == nullptr)
			return GENERALERROR;

		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		SkillManager* skillManager = SkillManager::instance();

		if (skillManager == nullptr)
			return GENERALERROR;

		if (!skillManager->canRevokeSkills(creature)) {
			creature->sendSystemMessage("@error_message:insufficient_permissions");
			return INSUFFICIENTPERMISSION;
		}

		ManagedReference<SceneObject*> object = target == 0 ? creature : server->getZoneServer()->getObject(target).get();

		if (object == nullptr || !object->isPlayerCreature())
			return INVALIDTARGET;

		CreatureObject* targetCreature = object->asCreatureObject();

		if (targetCreature == nullptr)
			return INVALIDTARGET;

		skillManager->requestSkillRevocation(creature, targetCreature, arguments.toString().trim().toLowerCase());

		return SUCCESS;
	}
};

#endif // REVOKESKILLCOMMAND_H_
