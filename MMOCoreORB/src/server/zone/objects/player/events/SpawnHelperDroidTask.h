/*
 				Copyright <SWGEmu>
		See file COPYING for copying conditions. */

/**
 * SpawnHelperDroidTask.h
 *
 *  Created: Monday May 9, 2022
 *   Author: H
 *
 */

#ifndef SPAWNHELPERDROIDTASK_H_
#define SPAWNHELPERDROIDTASK_H_

#include "conf/ConfigManager.h"
#include "server/zone/Zone.h"
#include "server/zone/ZoneServer.h"
#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/creature/ai/HelperDroidObject.h"
#include "server/zone/managers/creature/CreatureTemplateManager.h"
#include "server/zone/objects/creature/ai/CreatureTemplate.h"
#include "server/zone/managers/creature/CreatureManager.h"
#include "server/zone/managers/creature/PetManager.h"
#include "server/zone/managers/director/DirectorManager.h"
#include "server/zone/objects/intangible/PetControlDevice.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/managers/stringid/StringIdManager.h"

class SpawnHelperDroidTask: public Task {
	ManagedWeakReference<CreatureObject*> player;
	bool fromSceneReady;
	bool onLogin;

public:
	SpawnHelperDroidTask(CreatureObject* creature, bool fromSceneReady = false, bool onLogin = false) {
		player = creature;
		this->fromSceneReady = fromSceneReady;
		this->onLogin = onLogin;
	}

	void run() {
		CreatureObject* playerCreo = player.get();

		if (playerCreo == nullptr)
			return;

		ZoneServer* zoneServer = playerCreo->getZoneServer();

		if (zoneServer == nullptr)
			return;

		String controlDeviceObjectTemplate = "object/intangible/pet/nhelper_droid.iff";
		String mobileTemplate = "helper_r2_unit";
		String generatedObjectTemplate = "object/mobile/nhelper_droid.iff";

		Locker plock(playerCreo);

		if (!ConfigManager::instance()->isHelperDroidEnabled())
			return;

		PlayerObject* ghost = playerCreo->getPlayerObject();
		Zone* zone = playerCreo->getZone();

		if (ghost == nullptr || !ghost->isOnline() || zone == nullptr || zone->getZoneName() == "tutorial" ||
			ghost->getScreenPlayData("HelperDroid", "manuallyDeleted") == "1")
			return;

		// Login only repairs the datapad and is allowed while loading, including
		// space logins. A queued summon must still wait for a usable ground scene.
		if (!onLogin && (ghost->isOnLoadScreen() || ghost->isTeleporting() || zone->isSpaceZone()))
			return;

		const bool shouldCall = !onLogin && (!fromSceneReady || ConfigManager::instance()->isHelperDroidAutoCallOnZoneEnabled());

		SceneObject* datapad = playerCreo->getSlottedObject("datapad");

		if (datapad == nullptr) {
			return;
		}

		// Check for already existing helper droid
		for (int i = 0; i < datapad->getContainerObjectsSize(); i++) {
			Reference<SceneObject*> obj =  datapad->getContainerObject(i).castTo<SceneObject*>();

			if (obj != nullptr && obj->isPetControlDevice()) {
				Reference<PetControlDevice*> controlDevice = cast<PetControlDevice*>(obj.get());

				if (controlDevice != nullptr && controlDevice->getPetType() == PetManager::HELPERDROIDPET) {
					ManagedReference<HelperDroidObject*> helperDroidObject = dynamic_cast<HelperDroidObject*>(controlDevice->getControlledObject());

					if (helperDroidObject != nullptr) {
						if (!shouldCall)
							return;

						Locker lock(controlDevice);
						Locker clock(helperDroidObject, playerCreo);

						controlDevice->callObject(playerCreo);
						return;
					}
				}
			}
		}

		CreatureManager* creatureManager = zone->getCreatureManager();

		// Space zones have no creature manager. Creating a stored helper only
		// needs a manager's object/child factory; it does not place it in that zone.
		if (creatureManager == nullptr && onLogin) {
			for (int i = 0; i < zoneServer->getZoneCount(); ++i) {
				auto groundZone = zoneServer->getZone(i);

				if (groundZone != nullptr && !groundZone->isSpaceZone()) {
					creatureManager = groundZone->getCreatureManager();

					if (creatureManager != nullptr)
						break;
				}
			}
		}

		if (creatureManager == nullptr)
			return;

		CreatureTemplate* creatureTemplate =  CreatureTemplateManager::instance()->getTemplate(mobileTemplate.hashCode());

		if (creatureTemplate == nullptr) {
			return;
		}

		ManagedReference<PetControlDevice*> controlDevice = zoneServer->createObject(controlDeviceObjectTemplate.hashCode(), 1).castTo<PetControlDevice*>();

		if (controlDevice == nullptr) {
			return;
		}

		Locker cdlocker(controlDevice);

		Reference<CreatureObject*> creatureObject = creatureManager->createCreature(generatedObjectTemplate.hashCode(), true, mobileTemplate.hashCode());

		if (creatureObject == nullptr) {
			controlDevice->destroyObjectFromDatabase(true);
			return;
		}

		Locker clocker(creatureObject, playerCreo);

		Reference<HelperDroidObject*> helperdroid = creatureObject.castTo<HelperDroidObject*>();

		if (helperdroid == nullptr) {
			controlDevice->destroyObjectFromDatabase(true);
			creatureObject->destroyObjectFromDatabase(true);
			return;
		}

		helperdroid->loadTemplateData(creatureTemplate);
		helperdroid->createChildObjects();
		helperdroid->setControlDevice(controlDevice);

		StringId s;
		s.setStringId(helperdroid->getObjectName()->getFullPath());
		controlDevice->setObjectName(s, false);
		controlDevice->setPetType(PetManager::HELPERDROIDPET);
		controlDevice->setControlledObject(creatureObject);
		controlDevice->setMaxVitality(100);
		controlDevice->setVitality(100);

		if (!datapad->transferObject(controlDevice, -1)) {
			controlDevice->destroyObjectFromDatabase(true);
			creatureObject->destroyObjectFromDatabase(true);
			return;
		}

		datapad->broadcastObject(controlDevice, true);

		if (onLogin) {
			// Existing quest observers must follow the replacement object without
			// requiring a greeting or changing their saved progress.
			DirectorManager::instance()->setSharedMemoryValue(String::valueOf(playerCreo->getObjectID()) + ":HelperDroidID:", helperdroid->getObjectID());

			// The next scene-ready event must not immediately call the replacement,
			// even when regular zone recalls are enabled.
			ghost->setScreenPlayData("HelperDroid", "loginProvisioned", "1");
			return;
		}

		// Introduce a newly created helper on the player's first planet arrival.
		// AutoCallOnZone only suppresses later scene-ready calls of an existing helper.
		controlDevice->callObject(playerCreo);
	}
};

#endif /* SPAWNHELPERDROIDTASK_H_ */
