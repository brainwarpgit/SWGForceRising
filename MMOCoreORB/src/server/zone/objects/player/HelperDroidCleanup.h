/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions. */

#ifndef HELPERDROIDCLEANUP_H_
#define HELPERDROIDCLEANUP_H_

#include "server/zone/ZoneServer.h"
#include "server/zone/managers/creature/PetManager.h"
#include "server/zone/managers/director/DirectorManager.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/creature/ai/AiAgent.h"
#include "server/zone/objects/intangible/PetControlDevice.h"
#include "server/zone/objects/intangible/ShipControlDevice.h"
#include "server/zone/objects/intangible/tasks/StorePetTask.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/ship/ShipObject.h"

class HelperDroidCleanup {
	static void clearShipAssignment(CreatureObject* player, ShipObject* ship, uint64 deviceID) {
		if (ship == nullptr)
			return;

		Locker shipLock(ship, player);

		if (ship->getOwner().get() != player || ship->getShipDroidID() != deviceID)
			return;

		ship->setShipDroidID(0, true);

		// Stored ships may share the device; only the current ship supplied
		// the player's active droid programs.
		if (player->getRootParent() == ship) {
			auto ghost = player->getPlayerObject();

			if (ghost != nullptr)
				ghost->removeDroidCommands();
		}
	}

public:
	static bool isHelperDevice(SceneObject* object) {
		if (object == nullptr || !object->isPetControlDevice())
			return false;

		auto device = dynamic_cast<PetControlDevice*>(object);

		if (device == nullptr)
			return false;

		auto controlled = device->getControlledObject();

		return device->getPetType() == PetManager::HELPERDROIDPET ||
			device->getServerObjectCRC() == STRING_HASHCODE("object/intangible/pet/nhelper_droid.iff") ||
			(controlled != nullptr && controlled->isHelperDroidObject());
	}

	// The caller holds the player lock. This does not change quest progress or
	// record a manual deletion; the successful player command owns that choice.
	static bool remove(CreatureObject* player, PetControlDevice* device) {
		if (player == nullptr || device == nullptr || !isHelperDevice(device))
			return false;

		ManagedReference<CreatureObject*> playerRef = player;
		ManagedReference<PetControlDevice*> deviceRef = device;
		auto zoneServer = playerRef->getZoneServer();
		auto ghost = playerRef->getPlayerObject();

		// Normal pet storage defers itself during loading. Deletion must wait
		// for its world cleanup to finish, and needs a zone to detach the device.
		if (zoneServer == nullptr || zoneServer->isServerLoading() || zoneServer->isServerShuttingDown() ||
			ghost == nullptr || player->getZone() == nullptr)
			return false;

		Locker deviceLock(device, player);

		if (!deviceRef->isASubChildOf(player))
			return false;

		ManagedReference<TangibleObject*> controlled = device->getControlledObject();
		ManagedReference<AiAgent*> pet = controlled.castTo<AiAgent*>();

		if (controlled != nullptr && pet == nullptr)
			return false;

		const uint64 deviceID = device->getObjectID();
		ManagedReference<SceneObject*> datapad = player->getSlottedObject("datapad");

		if (datapad != nullptr) {
			for (int i = 0; i < datapad->getContainerObjectsSize(); ++i) {
				auto object = datapad->getContainerObject(i);

				if (object == nullptr || !object->isShipControlDevice())
					continue;

				auto shipDevice = dynamic_cast<ShipControlDevice*>(object.get());

				if (shipDevice != nullptr) {
					ManagedReference<ShipObject*> ship = dynamic_cast<ShipObject*>(shipDevice->getControlledObject());
					clearShipAssignment(player, ship, deviceID);
				}
			}
		}

		ManagedReference<ShipObject*> currentShip = dynamic_cast<ShipObject*>(player->getRootParent());
		clearShipAssignment(player, currentShip, deviceID);

		if (pet != nullptr) {
			ManagedReference<ShipObject*> droidShip = dynamic_cast<ShipObject*>(pet->getRootParent());
			clearShipAssignment(player, droidShip, deviceID);

			Locker petLock(pet, player);

			// An already stored helper has no live effects to unload. Storing
			// it again could clear skill mods supplied by another active droid.
			if (pet->getLocalZone() != nullptr || pet->getParent().get() != nullptr ||
				pet->getLinkedCreature().get() != nullptr || ghost->hasActivePet(pet)) {
				// Calling storeObject would enqueue this work and race deletion.
				Reference<StorePetTask*> storeTask = new StorePetTask(player, pet);
				storeTask->run();
			}

			if (pet->getLocalZone() != nullptr || pet->getParent().get() != nullptr || ghost->hasActivePet(pet))
				return false;
		}

		// Detaching first also prevents an older delayed call from spawning
		// this device again, without cancelling another pet's pending call.
		device->destroyObjectFromWorld(true);

		if (device->isASubChildOf(player))
			return false;

		if (pet != nullptr) {
			DirectorManager::instance()->removeSharedMemoryValueIfEqual(
				String::valueOf(player->getObjectID()) + ":HelperDroidID:", pet->getObjectID());
		}

		device->destroyObjectFromDatabase(true);
		return true;
	}
};

#endif // HELPERDROIDCLEANUP_H_
