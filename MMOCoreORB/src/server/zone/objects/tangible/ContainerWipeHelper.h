#ifndef CONTAINERWIPEHELPER_H_
#define CONTAINERWIPEHELPER_H_

#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/scene/SceneObject.h"

class ContainerWipeHelper {
public:
	static bool hasProtectedContents(SceneObject* object) {
		if (object == nullptr || object->isNoTrade() || object->isResourceContainer() ||
				object->containsNoTradeObjectRecursive())
			return true;

		for (int i = 0; i < object->getContainerObjectsSize(); ++i) {
			if (hasProtectedContents(object->getContainerObject(i)))
				return true;
		}
		return false;
	}

	static bool isWipeable(SceneObject* child, CreatureObject* player, bool inventoryWipe) {
		return child != nullptr && !hasProtectedContents(child) &&
				(!inventoryWipe || !child->isContainerObject() || child->getContainerObjectsSize() == 0) &&
				child->canBeDestroyed(player) == 0;
	}

	static int countWipeable(SceneObject* target, CreatureObject* player, bool inventoryWipe) {
		int count = 0;
		for (int i = 0; i < target->getContainerObjectsSize(); ++i) {
			SceneObject* child = target->getContainerObject(i);
			if (isWipeable(child, player, inventoryWipe))
				++count;
		}
		return count;
	}

	static void collectWipeable(SceneObject* target, CreatureObject* player, bool inventoryWipe, Vector<uint64>& ids) {
		for (int i = 0; i < target->getContainerObjectsSize(); ++i) {
			SceneObject* child = target->getContainerObject(i);
			if (isWipeable(child, player, inventoryWipe))
				ids.add(child->getObjectID());
		}
	}

	static bool canWipe(SceneObject* container, CreatureObject* player, bool inventoryWipe) {
		if (container == nullptr || player == nullptr || player->getPlayerObject() == nullptr ||
				player->isInCombat() || player->getCurrentSpeed() > 0.f || !container->isASubChildOf(player))
			return false;

		SceneObject* parent = container->getParent().get();
		bool equippedWearable = container->isWearableContainerObject() && parent == player;
		if (inventoryWipe) {
			SceneObject* inventory = player->getSlottedObject("inventory");
			return equippedWearable && inventory != nullptr && countWipeable(inventory, player, true) > 0;
		}

		return parent != player && countWipeable(container, player, false) > 0;
	}
};

#endif
