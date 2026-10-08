#include "server/zone/objects/tangible/components/droid/DroidAutoLootObserver.h"
#include "server/zone/objects/tangible/components/droid/DroidAutoLootModuleDataComponent.h"
#include "server/zone/objects/creature/events/DroidAutoLootQueueTask.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "templates/params/ObserverEventType.h"

int DroidAutoLootObserverImplementation::notifyObserverEvent(unsigned int eventType, Observable* observable, ManagedObject* arg1, int64 arg2) {
	if (eventType != ObserverEventType::KILLEDCREATURE)
		return 1;
	auto source = module.get();
	auto owner = cast<CreatureObject*>(observable);
	auto corpse = cast<CreatureObject*>(arg1);
	if (source == nullptr || !source->isActive() || owner == nullptr || corpse == nullptr ||
			!corpse->isAiAgent() || corpse->isPlayerCreature() || !owner->isInRange(corpse, 64.f))
		return 1;
	Reference<Task*> task = new DroidAutoLootQueueTask(source, corpse);
	corpse->addPendingTask("droid_auto_loot_queue", task, 1000);
	return 0;
}
