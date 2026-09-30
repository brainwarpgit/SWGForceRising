/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions. */

#ifndef FINDCOMMAND_H_
#define FINDCOMMAND_H_

#include "server/zone/objects/player/sessions/FindSession.h"
#include "server/zone/managers/structure/StructureManager.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"

class FindCommand : public QueueCommand {
public:
	FindCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {
	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		if (!creature->isPlayerCreature())
			return GENERALERROR;

		try {
			StringTokenizer args(arguments.toString());

			ManagedReference<Facade*> facade = creature->getActiveSession(SessionFacadeType::FIND);
			ManagedReference<FindSession*> session = dynamic_cast<FindSession*>(facade.get());

			if (session == nullptr) {
				session = new FindSession(creature);
			}

			if (args.hasMoreTokens()) {
				String mapCategory = "";

				args.getStringToken(mapCategory);

				mapCategory = mapCategory.toLowerCase();

				if (mapCategory == "clear") {
					return clearFind(creature);
				}

				if (mapCategory == "lots") {
					return showAccountLots(creature);
				}

				if (mapCategory.contains(":"))
					mapCategory = mapCategory.replaceFirst(":", "_");

				String mapSubCategory = "";

				if (mapCategory.contains("_")) {
					mapSubCategory = mapCategory;

					StringTokenizer mapTokens(mapCategory);
					String mapCat;

					mapTokens.setDelimeter("_");
					mapTokens.getStringToken(mapCat);

					mapCategory = mapCat;
				}

				if (!mapCategory.isEmpty())
					session->findPlanetaryObject(mapCategory, mapSubCategory);

			} else {
				session->initalizeFindMenu();
				return SUCCESS;
			}

		} catch (Exception& e) {
			creature->sendSystemMessage("@base_player:find_general_error"); // /Find was unable to complete your request. Please try again.
		}

		return SUCCESS;
	}

	int showAccountLots(CreatureObject* creature) const {
		PlayerObject* ghost = creature->getPlayerObject();
		StructureManager* structureManager = StructureManager::instance();
		if (ghost == nullptr || !structureManager->isAccountLotsReady()) {
			creature->sendSystemMessage("Account lot information is unavailable right now.");
			return GENERALERROR;
		}

		auto structureIDs = structureManager->getAccountStructureIDs(ghost);
		int maximum = structureManager->getMaximumAccountLots(ghost);
		int remaining = structureManager->getAccountLotsRemaining(ghost);
		ManagedReference<SuiListBox*> box = new SuiListBox(creature, 0);
		box->setPromptTitle("Account Structures and Lots");
		box->setPromptText("Lots used: " + String::valueOf(maximum - remaining) + " / " + String::valueOf(maximum)
				+ " | Available: " + String::valueOf(remaining)
				+ ". Each structure shows its assigned lots and current balances.");
		box->setForceCloseDisabled();

		for (uint64 structureID : structureIDs) {
			ManagedReference<StructureObject*> structure = creature->getZoneServer()->getObject(structureID).castTo<StructureObject*>();
			if (structure == nullptr || !structureManager->isOwnerAccount(structure->getOwnerObjectID(), ghost->getAccountID()))
				continue;

			String name = structure->getDisplayedName();
			ManagedReference<CityRegion*> city = structure->getCityRegion().get();
			if (city != nullptr)
				name += " / " + city->getCityRegionName();
			String details = name + " | Lots: " + String::valueOf(structure->getLotSize());
			if (!structure->isCivicStructure())
				details += " | Maintenance: " + String::valueOf((int)structure->getSurplusMaintenance()) + " cr";
			if (structure->isInstallationObject() && !structure->isGeneratorObject())
				details += " | Power: " + String::valueOf((int)structure->getSurplusPower());
			if (structure->isCityHall()) {
				if (city != nullptr)
					details += " | City Treasury: " + String::valueOf((int)city->getCityTreasury()) + " cr";
			}
			box->addMenuItem(details);
		}

		if (box->getMenuSize() == 0)
			box->addMenuItem("No account structures found.");
		ghost->addSuiBox(box);
		creature->sendMessage(box->generateMessage());
		return SUCCESS;
	}

	int clearFind(CreatureObject* player) const {
		if (player == nullptr || !player->isPlayerCreature())
			return GENERALERROR;

		PlayerObject* ghost = player->getPlayerObject();

		if (ghost == nullptr)
			return GENERALERROR;

		ghost->removeWaypointBySpecialType(WaypointObject::SPECIALTYPE_FIND, true);

		return SUCCESS;
	}
};

#endif // FINDCOMMAND_H_
