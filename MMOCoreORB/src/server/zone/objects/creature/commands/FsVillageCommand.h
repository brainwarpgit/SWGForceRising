#ifndef FSVILLAGECOMMAND_H_
#define FSVILLAGECOMMAND_H_

#include "server/zone/managers/director/DirectorManager.h"
#include "server/zone/managers/jedi/JediManager.h"

class FsVillageCommand : public QueueCommand {
public:
	FsVillageCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {
	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (creature == nullptr || !creature->isPlayerCreature())
			return GENERALERROR;

		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		if (creature->isInCombat()) {
			creature->sendSystemMessage("You cannot check the village phase while in combat.");
			return GENERALERROR;
		}

		if (JediManager::instance()->getJediProgressionType() != JediManager::VILLAGEJEDIPROGRESSION) {
			creature->sendSystemMessage("The Force Sensitive Village is not active.");
			return SUCCESS;
		}

		Lua* lua = DirectorManager::instance()->getLuaInstance();
		Reference<LuaFunction*> status = lua->createFunction("VillageJediManagerTownship", "showPhaseStatus", 0);
		*status << creature;
		status->callFunction();

		return SUCCESS;
	}
};

#endif // FSVILLAGECOMMAND_H_
