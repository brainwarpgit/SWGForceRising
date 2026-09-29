/*
 * DestroyStructureSessionImplementation.cpp
 *
 *  Created on: Jun 22, 2011
 *      Author: crush
 */

#include "server/zone/objects/player/sessions/DestroyStructureSession.h"
#include "server/zone/managers/structure/StructureManager.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/building/BuildingObject.h"
#include "server/zone/objects/player/sui/callbacks/DestroyStructureCodeSuiCallback.h"
#include "server/zone/objects/player/sui/callbacks/DestroyStructureRequestSuiCallback.h"
#include "server/zone/objects/player/sui/inputbox/SuiInputBox.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"
#include "server/zone/Zone.h"

#include "server/zone/managers/gcw/GCWManager.h"
#include "server/zone/managers/gcw/tasks/DestroyFactionInstallationTask.h"

namespace {
bool canDestroyStructure(CreatureObject* player, StructureObject* structure) {
	if (player == nullptr || !player->isPlayerCreature() || structure == nullptr || structure->getZone() == nullptr || structure->isPendingDestruction())
		return false;

	auto ghost = player->getPlayerObject();
	if (ghost == nullptr)
		return false;

	if (!structure->isOwnedByAccount(player) && !ghost->isStaff()) {
		player->sendSystemMessage("@player_structure:destroy_must_be_owner");
		return false;
	}
	if (structure->getAdditionalLots() > 0) {
		player->sendSystemMessage("Remove all added storage lots before destroying or redeeding this structure.");
		return false;
	}

	if (structure->isGCWBase() && !ghost->isStaff()) {
		auto gcwManager = structure->getZone()->getGCWManager();
		auto building = cast<BuildingObject*>(structure);
		if (gcwManager == nullptr || building == nullptr
				|| ((structure->getPvpStatusBitmask() & ObjectFlag::OVERT) && gcwManager->isBaseVulnerable(building)))
			return false;
	}

	String message = structure->getRedeedMessage();
	if (!message.isEmpty()) {
		player->sendSystemMessage("@player_structure:" + message);
		return false;
	}

	return true;
}
}

int DestroyStructureSessionImplementation::initializeSession() {
	if (creatureObject == nullptr || structureObject == nullptr)
		return cancelSession();

	Locker creatureLock(creatureObject);
	Locker _lock(structureObject, creatureObject);

	if (!canDestroyStructure(creatureObject, structureObject))
		return cancelSession();

	if (creatureObject->containsActiveSession(SessionFacadeType::DESTROYSTRUCTURE))
		return 1;

	creatureObject->addActiveSession(SessionFacadeType::DESTROYSTRUCTURE, _this.getReferenceUnsafeStaticCast());

	CreatureObject* player = cast<CreatureObject*>( creatureObject.get());

	String no = "\\#FF6347 @player_structure:can_redeed_no_suffix \\#.";
	String yes = "\\#32CD32 @player_structure:can_redeed_yes_suffix \\#.";

	String redeed = (structureObject->isRedeedable()) ? yes : no;

	StringBuffer maint;
	maint << "@player_structure:redeed_maintenance \\#" << ((structureObject->isRedeedable()) ? "32CD32 " : "FF6347 ") << structureObject->getSurplusMaintenance() << "/" << structureObject->getRedeedCost() << "\\#.";

	StringBuffer entry;
	entry << "@player_structure:confirm_destruction_d1 ";
	entry << "@player_structure:confirm_destruction_d2 \n\n";
	entry << "@player_structure:confirm_destruction_d3a ";
	entry << "\\#32CD32 @player_structure:confirm_destruction_d3b \\#. ";
	entry << "@player_structure:confirm_destruction_d4 \n";
	entry << "@player_structure:redeed_confirmation " << redeed;

	StringBuffer cond;
	cond << "@player_structure:redeed_condition \\#32CD32 " << (structureObject->getMaxCondition() - structureObject->getConditionDamage()) << "/" << structureObject->getMaxCondition() << "\\#.";

	ManagedReference<SuiListBox*> sui = new SuiListBox(player);
	sui->setCallback(new DestroyStructureRequestSuiCallback(creatureObject->getZoneServer(), _this.getReferenceUnsafeStaticCast()));
	sui->setCancelButton(true, "@no");
	sui->setOkButton(true, "@yes");
	sui->setUsingObject(structureObject);
	sui->setPromptTitle(structureObject->getDisplayedName());
	sui->setPromptText(entry.toString());

	sui->addMenuItem("@player_structure:can_redeed_alert " + redeed);
	sui->addMenuItem(cond.toString());
	sui->addMenuItem(maint.toString());

	player->getPlayerObject()->addSuiBox(sui);
	player->sendMessage(sui->generateMessage());

	return 0;
}

int DestroyStructureSessionImplementation::sendDestroyCode() {
	if (creatureObject == nullptr || structureObject == nullptr)
		return cancelSession();

	Locker creatureLock(creatureObject);
	Locker structureLock(structureObject, creatureObject);

	auto session = creatureObject->getActiveSession(SessionFacadeType::DESTROYSTRUCTURE).castTo<DestroyStructureSession*>();
	if (session != _this.getReferenceUnsafeStaticCast() || !canDestroyStructure(creatureObject, structureObject))
		return cancelSession();

	CreatureObject* player = cast<CreatureObject*>( creatureObject.get());

	destroyCode = System::random(899999) + 100000;

	String no = "\\#FF6347 @player_structure:will_not_redeed_confirm \\#.";
	String yes = "\\#32CD32 @player_structure:will_redeed_confirm \\#.";

	String redeed = (structureObject->isRedeedable()) ? yes : no;

	StringBuffer entry;
	entry << "@player_structure:your_structure_prefix ";
	entry << redeed << " @player_structure:will_redeed_suffix \n\n";
	entry << "Code: " << destroyCode;

	ManagedReference<SuiInputBox*> sui = new SuiInputBox(player);
	sui->setCallback(new DestroyStructureCodeSuiCallback(player->getZoneServer(), _this.getReferenceUnsafeStaticCast()));
	sui->setUsingObject(structureObject);
	sui->setPromptTitle("@player_structure:confirm_destruction_t"); //Confirm Structure Deletion
	sui->setPromptText(entry.toString());
	sui->setCancelButton(true, "@cancel");
	sui->setMaxInputSize(6);

	player->getPlayerObject()->addSuiBox(sui);
	player->sendMessage(sui->generateMessage());

	return 0;
}

int DestroyStructureSessionImplementation::destroyStructure() {
	if (creatureObject == nullptr || structureObject == nullptr)
		return cancelSession();

	Locker creatureLock(creatureObject);
	Locker structureLock(structureObject, creatureObject);

	auto session = creatureObject->getActiveSession(SessionFacadeType::DESTROYSTRUCTURE).castTo<DestroyStructureSession*>();
	if (session != _this.getReferenceUnsafeStaticCast() || !canDestroyStructure(creatureObject, structureObject))
		return cancelSession();

	creatureObject->sendSystemMessage("@player_structure:processing_destruction"); //Processing confirmed structure destruction...

	if (structureObject->isGCWBase()) {
		Zone* zone = structureObject->getZone();
		if (zone == nullptr)
			return cancelSession();

		GCWManager* gcwMan = zone->getGCWManager();
		if (gcwMan == nullptr)
			return cancelSession();

		Locker gcwLock(gcwMan, structureObject);
		if (!canDestroyStructure(creatureObject, structureObject))
			return cancelSession();

		gcwMan->doBaseDestruction(structureObject);
		return cancelSession();

	} else if(structureObject->isTurret() || structureObject->isMinefield() || structureObject->isScanner()){

		Reference<DestroyFactionInstallationTask*> destroyTask = new DestroyFactionInstallationTask(cast<InstallationObject*>(structureObject.get()));
		destroyTask->execute();

		return cancelSession();

	} else {
		StructureManager::instance()->redeedStructure(creatureObject);
	}
	return 0;
}

int DestroyStructureSessionImplementation::cancelSession() {
	if (creatureObject == nullptr)
		return 0;

	Locker locker(creatureObject);
	auto session = creatureObject->getActiveSession(SessionFacadeType::DESTROYSTRUCTURE).castTo<DestroyStructureSession*>();
	if (session == _this.getReferenceUnsafeStaticCast())
		creatureObject->dropActiveSession(SessionFacadeType::DESTROYSTRUCTURE);

	return 0;
}
