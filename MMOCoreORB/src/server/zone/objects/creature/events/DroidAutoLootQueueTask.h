#ifndef DROIDAUTOLOOTQUEUETASK_H_
#define DROIDAUTOLOOTQUEUETASK_H_

#include "server/zone/objects/tangible/components/droid/DroidAutoLootModuleDataComponent.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/creature/ai/DroidObject.h"

class DroidAutoLootQueueTask : public Task {
	Reference<DroidAutoLootModuleDataComponent*> module;
	ManagedWeakReference<CreatureObject*> corpse;

public:
	DroidAutoLootQueueTask(DroidAutoLootModuleDataComponent* source, CreatureObject* target) : Task() {
		module = source;
		corpse = target;
	}

	void run() {
		auto target = corpse.get();
		if (module == nullptr || target == nullptr || !module->isActive() || !target->isDead())
			return;
		auto droid = module->getDroidObject();
		if (droid == nullptr)
			return;
		auto owner = droid->getLinkedCreature().get();
		if (owner == nullptr || !owner->isInRange(target, 64.f))
			return;
		auto inventory = target->getSlottedObject("inventory");
		const ContainerPermissions* permissions = inventory != nullptr ? inventory->getContainerPermissions() : nullptr;
		if (permissions != nullptr && permissions->getOwnerID() == owner->getObjectID()) {
			module->addLootTarget(target->getObjectID());
			droid->activateAiBehavior(true);
		}
	}
};

#endif
