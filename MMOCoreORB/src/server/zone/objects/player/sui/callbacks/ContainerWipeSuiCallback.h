#ifndef CONTAINERWIPESUICALLBACK_H_
#define CONTAINERWIPESUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/SuiBox.h"
#include "server/zone/objects/tangible/ContainerWipeHelper.h"

class ContainerWipeSuiCallback : public SuiCallback {
	bool wipeInventory;
	Vector<uint64> itemIDs;

public:
	ContainerWipeSuiCallback(ZoneServer* server, bool inventory, const Vector<uint64>& ids)
			: SuiCallback(server), wipeInventory(inventory), itemIDs(ids) {
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isMessageBox() || eventIndex != 0)
			return;

		ManagedReference<SceneObject*> container = sui->getUsingObject().get();
		if (!ContainerWipeHelper::canWipe(container, player, wipeInventory)) {
			player->sendSystemMessage("The wipe was canceled because its requirements are no longer met.");
			return;
		}

		ManagedReference<SceneObject*> target = container;
		if (wipeInventory)
			target = player->getSlottedObject("inventory");
		if (target == nullptr)
			return;

		Locker targetLock(target, player);
		if (!ContainerWipeHelper::canWipe(container, player, wipeInventory))
			return;

		int deleted = 0;
		for (int i = 0; i < itemIDs.size(); ++i) {
			ManagedReference<SceneObject*> child = server->getObject(itemIDs.get(i));
			if (child == nullptr || child->getParent().get() != target.get() ||
					!ContainerWipeHelper::isWipeable(child, player, wipeInventory))
				continue;

			Locker childLock(child, target);
			if (child->getParent().get() != target.get() ||
					!ContainerWipeHelper::isWipeable(child, player, wipeInventory))
				continue;
			child->destroyObjectFromWorld(true);
			child->destroyObjectFromDatabase(true);
			++deleted;
		}

		player->sendSystemMessage(String::valueOf(deleted) + " item(s) deleted. No-trade items and resources were kept." +
				(wipeInventory ? String(" Nonempty containers were also kept.") : String("")));
	}
};

#endif
