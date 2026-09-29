/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef ADJUSTLOTCOUNTCOMMAND_H_
#define ADJUSTLOTCOUNTCOMMAND_H_

#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/managers/structure/StructureManager.h"
#include "server/login/account/Account.h"
#include <cerrno>
#include <cstdlib>
#include <limits>

class AdjustLotCountCommand : public QueueCommand {
public:

	AdjustLotCountCommand(const String& name, ZoneProcessServer* server)
		: QueueCommand(name, server) {

	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {

		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		auto zoneServer = creature->getZoneServer();

		if (zoneServer == nullptr)
			return GENERALERROR;

		ManagedReference<SceneObject*> targetObject = zoneServer->getObject(target);

		if (targetObject == nullptr || !targetObject->isPlayerCreature())
			return INVALIDTARGET;

		CreatureObject* targetCreature = cast<CreatureObject*>( targetObject.get());

		ManagedReference<PlayerObject*> ghost = targetCreature->getPlayerObject();

		if (ghost == nullptr)
			return INVALIDPARAMETERS;

		ManagedReference<Account*> account = ghost->getAccount();

		if (account == nullptr)
			return GENERALERROR;

		if (ghost->getAccountID() == 0 || account->getAccountID() != ghost->getAccountID()) {
			creature->sendSystemMessage("The target's account information is unavailable. No lot adjustment was made.");
			return GENERALERROR;
		}

		if (!StructureManager::instance()->isAccountLotsReady()) {
			creature->sendSystemMessage("Account lot data is unavailable. No lot adjustment was made.");
			return GENERALERROR;
		}

		int lotCount = 0;

		try {
			StringTokenizer tokenizer(arguments.toString());
			String amount;

			if (!tokenizer.hasMoreTokens()) {
				creature->sendSystemMessage("SYNTAX: /adjustLotCount <signed lot adjustment> (applies to the target's account in this galaxy)");
				return INVALIDPARAMETERS;
			}

			tokenizer.getStringToken(amount);
			char* end = nullptr;
			errno = 0;
			const long long parsedAmount = std::strtoll(amount.toCharArray(), &end, 10);

			if (tokenizer.hasMoreTokens() || end == amount.toCharArray() || *end != '\0' || errno == ERANGE ||
				parsedAmount < std::numeric_limits<int>::min() || parsedAmount > std::numeric_limits<int>::max()) {
				creature->sendSystemMessage("SYNTAX: /adjustLotCount <signed lot adjustment> (applies to the target's account in this galaxy)");
				return INVALIDPARAMETERS;
			}

			lotCount = static_cast<int>(parsedAmount);

		} catch (Exception& e) {
			creature->sendSystemMessage("SYNTAX: /adjustLotCount <signed lot adjustment> (applies to the target's account in this galaxy)");
			return INVALIDPARAMETERS;
		}

		const uint32 galaxyID = zoneServer->getGalaxyID();

		// Migrate any existing character-specific allowances before applying
		// an administrator's new adjustment to the shared account bonus.
		ghost->getMaximumLots();

		if (!account->adjustStructureLotBonus(galaxyID, lotCount)) {
			creature->sendSystemMessage("The account lot adjustment would exceed the supported integer range. No change was made.");
			return INVALIDPARAMETERS;
		}

		StringBuffer message;
		message << "Adjusted " << targetCreature->getFirstName() << "'s shared account lot allowance in this galaxy by " << lotCount
			<< ". Account bonus: " << account->getStructureLotBonus(galaxyID)
			<< "; total account lots: " << ghost->getMaximumLots() << ".";
		creature->sendSystemMessage(message.toString());

		return SUCCESS;
	}

};

#endif //ADJUSTLOTCOUNTCOMMAND_H_
