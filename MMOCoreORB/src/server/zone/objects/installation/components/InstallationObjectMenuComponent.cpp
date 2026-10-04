/*
 * InstallationObjectMenuComponent.cpp
 *
 *  Created on: Feb 27, 2012
 *      Author: xyborn
 */

#include "InstallationObjectMenuComponent.h"
#include "server/zone/Zone.h"
#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/packets/object/ObjectMenuResponse.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/installation/InstallationObject.h"
#include "server/zone/managers/structure/StructureManager.h"
#include "server/zone/objects/intangible/PetControlDevice.h"
#include "server/zone/managers/creature/PetManager.h"

void InstallationObjectMenuComponent::fillObjectMenuResponse(SceneObject* sceneObject, ObjectMenuResponse* menuResponse, CreatureObject* player) const {
	if (!sceneObject->isInstallationObject())
		return;

	InstallationObject* installation = cast<InstallationObject*>(sceneObject);

	if (!installation->isOnAdminList(player))
		return;

	if (installation->isOwnedByAccount(player)) {
		bool canWithdrawResources = false;
		if (installation->isHarvesterObject() || installation->isGeneratorObject()) {
			HopperList* hopper = installation->getHopperList();
			for (int i = 0; i < hopper->size(); ++i) {
				ResourceContainer* container = hopper->get(i);
				if (container != nullptr && container->getQuantity() > 0 && container->getSpawnObject() != nullptr) {
					canWithdrawResources = true;
					break;
				}
			}
		}
		bool showMaintenance = installation->getQuickMaintenanceAmount() > 0;
		bool showPower = !installation->isGeneratorObject() && installation->getQuickPowerAmount() > 0;
		if (showMaintenance || showPower || canWithdrawResources)
			menuResponse->addRadialMenuItem(243, 3, "Quick Options");
		if (showMaintenance)
			menuResponse->addRadialMenuItemToRadialID(243, 244, 3, StructureManager::formatQuickAmount(installation->getQuickMaintenanceAmount()) + " Maintenance");
		if (showPower)
			menuResponse->addRadialMenuItemToRadialID(243, 245, 3, StructureManager::formatQuickAmount(installation->getQuickPowerAmount()) + " Power");
		if (canWithdrawResources)
			menuResponse->addRadialMenuItemToRadialID(243, 246, 3, "Withdraw All Resources");
	}
	menuResponse->addRadialMenuItem(118, 3, "@player_structure:management");
	menuResponse->addRadialMenuItemToRadialID(118, 128, 3, "@player_structure:permission_destroy"); //Destroy Structure
	menuResponse->addRadialMenuItemToRadialID(118, 124, 3, "@player_structure:management_status"); //Status
	menuResponse->addRadialMenuItemToRadialID(118, 129, 3, "@player_structure:management_pay"); //Pay Maintenance
	PlayerObject* ghost = player->getPlayerObject();
	bool canWithdraw = installation->isOwnedByAccount(player) || (ghost != nullptr && ghost->isAdmin());
	if (canWithdraw)
		menuResponse->addRadialMenuItemToRadialID(118, 70, 3, "@player_structure:take_maintenance"); // Withdraw Maintenance
	if (!installation->isGeneratorObject()) {
		menuResponse->addRadialMenuItemToRadialID(118, 51, 3, "@player_structure:management_power"); // Deposit Power
		if (canWithdraw)
			menuResponse->addRadialMenuItemToRadialID(118, 71, 3, "Withdraw Power");
	}
	if (installation->isOwnedByAccount(player)) {
		menuResponse->addRadialMenuItemToRadialID(118, 247, 3, "Set Quick Maintenance Amount");
		if (!installation->isGeneratorObject())
			menuResponse->addRadialMenuItemToRadialID(118, 248, 3, "Set Quick Power Amount");
	}

	if (StructureManager::instance()->canTakeOwnership(player, installation))
		menuResponse->addRadialMenuItemToRadialID(118, 240, 3, "Take Ownership");

	ManagedReference<SceneObject*> datapad = player->getSlottedObject("datapad");
	if(datapad != nullptr) {
		for (int i = 0; i < datapad->getContainerObjectsSize(); ++i) {
			ManagedReference<SceneObject*> object = datapad->getContainerObject(i);

			if (object != nullptr && object->isPetControlDevice()) {
				PetControlDevice* device = cast<PetControlDevice*>( object.get());

				if (device->getPetType() == PetManager::DROIDPET) {
					menuResponse->addRadialMenuItemToRadialID(118, 131, 3, "@player_structure:assign_droid"); //Assign Droid
					break;
				}
			}
		}
	}
	menuResponse->addRadialMenuItemToRadialID(118, 50, 3, "@base_player:set_name"); //Set Name

	menuResponse->addRadialMenuItem(117, 3, "@player_structure:permissions"); //Structure Permissions
	menuResponse->addRadialMenuItemToRadialID(117, 121, 3, "@player_structure:permission_admin"); //Administrator List
	menuResponse->addRadialMenuItemToRadialID(117, 123, 3, "@player_structure:permission_hopper"); //Hopper List

}

int InstallationObjectMenuComponent::handleObjectMenuSelect(SceneObject* sceneObject, CreatureObject* player, byte selectedID) const {
	if (!sceneObject->isInstallationObject())
		return 1;

	InstallationObject* installation = cast<InstallationObject*>(sceneObject);

	ManagedReference<Zone*> zone = installation->getZone();

	if (zone == nullptr)
		return 1;

	if (selectedID == 240)
		return StructureManager::instance()->takeOwnership(player, installation);

	StructureManager* structureManager = StructureManager::instance();
	if (selectedID == 244) {
		structureManager->quickPayMaintenance(installation, player);
		return 0;
	}
	if (selectedID == 245) {
		structureManager->quickDepositPower(installation, player);
		return 0;
	}
	if (selectedID == 246) {
		structureManager->withdrawAllResources(installation, player);
		return 0;
	}
	if (selectedID == 247 || selectedID == 248) {
		structureManager->promptQuickAmount(installation, player, selectedID == 248);
		return 0;
	}

	if (!installation->isOnAdminList(player))
		return 1;

	switch (selectedID) {
	case 124:
		player->executeObjectControllerAction(0x13F7E585, installation->getObjectID(), ""); //structureStatus
		break;

	case 129:
		player->executeObjectControllerAction(0xE7E35B30, installation->getObjectID(), ""); //payMaintenance
		break;
	case 70: {
		Locker locker(installation, player);
		structureManager->promptWithdrawMaintenance(installation, player);
		break;
	}
	case 71: {
		Locker locker(installation, player);
		structureManager->promptWithdrawPower(installation, player);
		break;
	}

	case 128:
		player->executeObjectControllerAction(0x18FC1726, installation->getObjectID(), ""); //destroyStructure command
		break;

	case 131:
		structureManager->promptMaintenanceDroid(installation,player);
		break;
	case 50:
		structureManager->promptNameStructure(player, installation, installation);
		//player->executeObjectControllerAction(0xC367B461, installation->getObjectID(), ""); //nameStructure
		break;

	case 51:
		//TODO: Move to structure manager.
		if (!installation->isGeneratorObject()) {
			installation->handleStructureAddEnergy(player);
		}
		break;

	case 121:
		installation->sendPermissionListTo(player, "ADMIN");
		break;

	case 123:
		installation->sendPermissionListTo(player, "HOPPER");
		break;


	default:
		break;
	}

	return 0;
}
