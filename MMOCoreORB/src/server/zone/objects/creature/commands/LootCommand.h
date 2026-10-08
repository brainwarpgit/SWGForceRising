/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef LOOTCOMMAND_H_
#define LOOTCOMMAND_H_

#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/managers/player/PlayerManager.h"
#include "server/zone/managers/group/GroupLootTask.h"
#include "server/zone/objects/transaction/TransactionLog.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/Zone.h"

class LootCommand : public QueueCommand {

public:
	enum {
		NOPICKUPITEMS = 0,
		ITEMFOROTHER = 1,
		PICKEDANDREMAINING = 2,
		PICKEDANDEMPTY = 3
	};

	LootCommand(const String& name, ZoneProcessServer* server)
		: QueueCommand(name, server) {

	}

	void lootNearbyCorpses(CreatureObject* creature, AiAgent* selectedCorpse, PlayerManager* playerManager) const {
		Zone* zone = creature->getZone();
		if (zone == nullptr)
			return;
		ManagedReference<GroupObject*> group = creature->getGroup();
		if (group != nullptr && (!group->isAreaLootEnabled() || group->getLootRule() == GroupManager::MASTERLOOTER))
			return;
		if (group == nullptr && (creature->getPlayerObject() == nullptr || !creature->getPlayerObject()->isAreaLootEnabled()))
			return;
		uint64 ownerID = group != nullptr ? group->getObjectID() : creature->getObjectID();

		Vector3 position = creature->getWorldPosition();
		SortedVector<TreeEntry*> objects(512, 512);
		zone->getInRangeObjects(position.getX(), position.getZ(), position.getY(), 64, &objects, true);

		for (int i = 0; i < objects.size(); ++i) {
			SceneObject* object = static_cast<SceneObject*>(objects.get(i));
			if (object == nullptr || object == selectedCorpse || !object->isAiAgent())
				continue;

			ManagedReference<AiAgent*> nearby = object->asAiAgent();
			if (nearby == nullptr || nearby->getZone() != zone || nearby->getParentID() != creature->getParentID() ||
					!checkDistance(nearby, creature, 64))
				continue;

			Locker nearbyLocker(nearby, creature);
			if (!nearby->isDead() || creature->isDead() || creature->getGroup() != group ||
					(group != nullptr && (!group->isAreaLootEnabled() || group->getLootRule() == GroupManager::MASTERLOOTER)))
				continue;

			SceneObject* inventory = nearby->getSlottedObject("inventory");
			const ContainerPermissions* permissions = inventory != nullptr ? inventory->getContainerPermissions() : nullptr;
			if (permissions == nullptr || permissions->getOwnerID() != ownerID)
				continue;

			if (group == nullptr)
				playerManager->lootAll(creature, nearby);
			else {
				GroupLootTask* task = new GroupLootTask(group, creature, nearby, true);
				task->execute();
			}
		}
	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		ZoneServer* zoneServer = server->getZoneServer();

		if (zoneServer == nullptr)
			return GENERALERROR;

		ManagedReference<SceneObject*> targetObject = zoneServer->getObject(target);

		if (targetObject == nullptr || !targetObject->isAiAgent())
			return INVALIDTARGET;

		AiAgent* agent = targetObject.castTo<AiAgent*>();

		if (agent == nullptr)
			return INVALIDTARGET;

		Locker locker(agent, creature);

		if (!agent->isDead() || creature->isDead())
			return GENERALERROR;

		if (!checkDistance(agent, creature, 16)) {
			creature->sendSystemMessage("@error_message:target_out_of_range"); //"Your target is out of range for this action."
			return GENERALERROR;
		}

		bool lootAll = arguments.toString().beginsWith("all");

		// Get the corpse's inventory.
		SceneObject* lootContainer = agent->getSlottedObject("inventory");

		if (lootContainer == nullptr) {
			return GENERALERROR;
		}

		PlayerManager* playerManager = zoneServer->getPlayerManager();

		if (playerManager == nullptr)
			return GENERALERROR;

		const ContainerPermissions* permissions = lootContainer->getContainerPermissions();

		if (permissions == nullptr)
			return GENERALERROR;

		// Determine the loot rights.
		uint64 ownerID = permissions->getOwnerID();

		bool looterIsOwner = (ownerID == creature->getObjectID());
		bool groupIsOwner = (ownerID == creature->getGroupID());

		// Allow player to loot the corpse if they own it.
		if (looterIsOwner) {
			if (lootAll) {
				bool areaLoot = creature->getGroup() == nullptr && creature->getPlayerObject() != nullptr &&
						creature->getPlayerObject()->isAreaLootEnabled();
				playerManager->lootAll(creature, agent);
				if (areaLoot) {
					locker.release();
					lootNearbyCorpses(creature, agent, playerManager);
				}
			} else {
				//Check if the corpse's inventory contains any items.
				if (lootContainer->getContainerObjectsSize() < 1) {
  					creature->sendSystemMessage("@error_message:corpse_empty"); //"You find nothing else of value on the selected corpse."
  					playerManager->rescheduleCorpseDestruction(creature, agent);
  				} else {
					agent->notifyObservers(ObserverEventType::LOOTCREATURE, creature, 0);
					lootContainer->openContainerTo(creature);
				}
			}

			return SUCCESS;
		}

		// If player and their group don't own the corpse, pick up any owned items left on corpse due to full inventory, then fail.
		if (!groupIsOwner) {
			int pickupResult = pickupOwnedItems(agent, creature, lootContainer);
			if (pickupResult < 2) { //Player didn't pickup an item nor is one available for them.
				StringIdChatParameter noPermission("error_message","no_corpse_permission"); //"You do not have permission to access this corpse."
				creature->sendSystemMessage(noPermission);
				return GENERALERROR;
			} else if (pickupResult == PICKEDANDEMPTY) {
				playerManager->rescheduleCorpseDestruction(creature, agent);
				return SUCCESS;
			}

			return SUCCESS;
		}

		// If looter's group is the owner, attempt to pick up any owned items, then process group loot rule.
		int pickupResult = pickupOwnedItems(agent, creature, lootContainer);

		switch (pickupResult) {
		case NOPICKUPITEMS: //No items available for anyone to pickup.
			break;
		case ITEMFOROTHER: //No items available for looter to pickup, but one is available for someone else.
			agent->notifyObservers(ObserverEventType::LOOTCREATURE, creature, 0);
			lootContainer->openContainerTo(creature);
			return SUCCESS;
		case PICKEDANDREMAINING: //An item was available for the looter, there are items remaining.
			return SUCCESS;
		case PICKEDANDEMPTY: //An item was available for the looter, there are NO items remaining.
			playerManager->rescheduleCorpseDestruction(creature, agent);
			return SUCCESS;
		default:
			break;
		}

		ManagedReference<GroupObject*> group = creature->getGroup();

		if (group == nullptr)
			return GENERALERROR;

		GroupLootTask* task = new GroupLootTask(group, creature, agent, lootAll);

		if (task != nullptr)
			task->execute();
		if (lootAll && group->isAreaLootEnabled() &&
				group->getLootRule() != GroupManager::MASTERLOOTER) {
			locker.release();
			lootNearbyCorpses(creature, agent, playerManager);
		}

		return SUCCESS;
	}

	int pickupOwnedItems(AiAgent* ai, CreatureObject* creature, SceneObject* lootContainer) const {
		/* Return codes:
		 * NOPICKUPITEMS: No items available for anyone to pickup.
		 * ITEMFOROTHER: No items available for looter to pickup, but one is available for someone else.
		 * PICKEDANDREMAINING: An item was available for the looter, there are items remaining.
		 * PICKEDANDEMPTY: An item was available for the looter, there are NO items remaining.
		 */

		bool attemptedPickup = false;
		bool pickupAvailableOther = false;

		int totalItems = lootContainer->getContainerObjectsSize();
		if (totalItems < 1) return NOPICKUPITEMS;

		ContainerPermissions* contPerms = lootContainer->getContainerPermissionsForUpdate();
		if (contPerms == nullptr) {
			return NOPICKUPITEMS;
		}

		SceneObject* playerInventory = creature->getSlottedObject("inventory");
		if (playerInventory == nullptr) {
			return NOPICKUPITEMS;
		}

		// Check each loot item to see if the player owns it.
		for (int i = totalItems - 1; i >= 0; --i) {
			SceneObject* object = lootContainer->getContainerObject(i);
			if (object == nullptr) continue;

			ContainerPermissions* itemPerms = object->getContainerPermissionsForUpdate();
			if (itemPerms == nullptr) continue;

			//Check if player owns the loot item.
			uint64 itemOwnerID = itemPerms->getOwnerID();
			if (itemOwnerID == creature->getObjectID()) {

				// Attempt to transfer the item to the player.
				attemptedPickup = true;
				if (playerInventory->isContainerFullRecursive()) {
					StringIdChatParameter full("group", "you_are_full"); //"Your Inventory is full."
					creature->sendSystemMessage(full);
					return PICKEDANDREMAINING;
				}

				uint64 originalOwner = contPerms->getOwnerID();
				contPerms->setOwner(creature->getObjectID());
				TransactionLog trx(ai, creature, object, TrxCode::NPCLOOTCLAIM);

				if (creature->getZoneServer()->getObjectController()->transferObject(object, playerInventory, -1, true)) {
					itemPerms->clearDenyPermission("player", ContainerPermissions::OPEN);
					itemPerms->clearDenyPermission("player", ContainerPermissions::MOVECONTAINER);
					trx.commit();
				} else {
					trx.abort() << "Failed to transferObject to player";
				}

				contPerms->setOwner(originalOwner);

			} else if (itemOwnerID != 0)
				pickupAvailableOther = true;
		}

		//Determine which result code to return.
		if (attemptedPickup) {
			if (lootContainer->getContainerObjectsSize() > 0)
				return PICKEDANDREMAINING;
			else
				return PICKEDANDEMPTY;
		}

		if (pickupAvailableOther)
			return ITEMFOROTHER;

		return NOPICKUPITEMS;
	}
};
#endif //LOOTCOMMAND_H_
