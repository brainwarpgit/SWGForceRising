#ifndef PETLOOTCOMMAND_H_
#define PETLOOTCOMMAND_H_

#include "server/zone/objects/creature/commands/QueueCommand.h"
#include "server/zone/objects/creature/ai/DroidObject.h"
#include "server/zone/objects/tangible/components/droid/DroidAutoLootModuleDataComponent.h"

class PetLootCommand : public QueueCommand {
public:
	PetLootCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {}

	int doQueueCommand(CreatureObject* creature, const uint64& targetID, const UnicodeString& arguments) const {
		auto droid = cast<DroidObject*>(creature);
		if (droid == nullptr || droid->isDead() || droid->isIncapacitated() || droid->isInCombat() || !droid->hasPower())
			return GENERALERROR;
		auto owner = droid->getLinkedCreature().get();
		if (owner == nullptr)
			return GENERALERROR;
		Locker ownerLock(owner);
		Locker droidLock(droid, owner);
		auto module = droid->getModule("auto_loot_module").castTo<DroidAutoLootModuleDataComponent*>();
		if (module == nullptr)
			return GENERALERROR;
		if (!module->isActive()) {
			owner->sendSystemMessage("Enable Auto Loot before using the target command.");
			return GENERALERROR;
		}
		ZoneServer* zoneServer = server->getZoneServer();
		SceneObject* target = zoneServer != nullptr ? zoneServer->getObject(targetID, true) : nullptr;
		if (target == nullptr || !target->isAiAgent() || !target->asCreatureObject()->isDead() ||
				!owner->isInRange(target, 64.f) ||
				owner->getParentID() != target->getParentID() || droid->getParentID() != target->getParentID()) {
			owner->sendSystemMessage("Select a nearby creature corpse to loot.");
			return GENERALERROR;
		}
		auto inventory = target->getSlottedObject("inventory");
		const ContainerPermissions* permissions = inventory != nullptr ? inventory->getContainerPermissions() : nullptr;
		if (permissions == nullptr || permissions->getOwnerID() != owner->getObjectID()) {
			owner->sendSystemMessage("You cannot loot that corpse.");
			return GENERALERROR;
		}
		module->addLootTarget(targetID, true);
		droid->activateAiBehavior(true);
		owner->sendSystemMessage("Loot target queued for your droid.");
		return SUCCESS;
	}
};

#endif
