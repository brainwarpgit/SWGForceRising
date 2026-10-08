#ifndef DROIDAUTOLOOTTASK_H_
#define DROIDAUTOLOOTTASK_H_

#include "server/zone/objects/tangible/components/droid/DroidAutoLootModuleDataComponent.h"
#include "server/zone/objects/creature/ai/DroidObject.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/managers/player/PlayerManager.h"
#include "server/zone/ZoneServer.h"

class DroidAutoLootTask : public Task {
	Reference<DroidAutoLootModuleDataComponent*> module;
	ManagedWeakReference<CreatureObject*> corpse;

public:
	DroidAutoLootTask(DroidAutoLootModuleDataComponent* source, CreatureObject* target)
		: Task() {
		module = source;
		corpse = target;
	}

	void run() {
		auto target = corpse.get();
		if (module == nullptr || target == nullptr || !module->isActive())
			return;
		auto droid = module->getDroidObject();
		if (droid == nullptr || !droid->hasPower() || droid->isDead() || droid->isIncapacitated())
			return;
		auto owner = droid->getLinkedCreature().get();
		if (owner == nullptr || owner->isDead() || owner->getZone() == nullptr ||
				owner->getZone() != target->getZone() || droid->getZone() != owner->getZone() ||
				owner->getParentID() != target->getParentID() || droid->getParentID() != target->getParentID() ||
				!owner->isInRange(target, 64.f) ||
				!droid->isInRange(target, 7.f + target->getTemplateRadius() + droid->getTemplateRadius()))
			return;
		Locker ownerLock(owner);
		Locker targetLock(target, owner);
		if (!target->isDead() || !module->isActive())
			return;
		SceneObject* inventory = target->getSlottedObject("inventory");
		const ContainerPermissions* permissions = inventory != nullptr ? inventory->getContainerPermissions() : nullptr;
		if (permissions == nullptr || permissions->getOwnerID() != owner->getObjectID())
			return;
		ZoneServer* zoneServer = owner->getZoneServer();
		PlayerManager* playerManager = zoneServer != nullptr ? zoneServer->getPlayerManager() : nullptr;
		if (playerManager != nullptr)
			playerManager->lootAllWithAutoLootBonus(owner, target, module->getCreditBonus());
	}
};

#endif
