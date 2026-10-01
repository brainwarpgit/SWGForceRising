/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef PERMISSIONLISTMODIFYCOMMAND_H_
#define PERMISSIONLISTMODIFYCOMMAND_H_

#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/objects/ship/PobShipObject.h"
#include "server/zone/ZoneServer.h"
#include "server/zone/managers/player/PlayerManager.h"
#include "server/zone/managers/guild/GuildManager.h"
#include "server/zone/objects/transaction/TransactionLog.h"
#include "server/zone/objects/guild/GuildStructurePermissionsTask.h"
#include "server/login/account/Account.h"
#include "server/login/account/AccountManager.h"
#include "server/login/objects/CharacterList.h"

class PermissionListModifyCommand : public QueueCommand {
public:
	PermissionListModifyCommand(const String& name, ZoneProcessServer* server) : QueueCommand(name, server) {
	}

	int doQueueCommand(CreatureObject* creature, const uint64& target, const UnicodeString& arguments) const {
		if (!checkStateMask(creature))
			return INVALIDSTATE;

		if (!checkInvalidLocomotions(creature))
			return INVALIDLOCOMOTION;

		// info(true) << "PermissionListPermissionListModifyCommand called -- by " << creature->getDisplayedName() << " Target ID :" << target << " Arguments: " << arguments.toString();

		ManagedReference<PlayerManager*> playerManager = server->getPlayerManager();

		if (playerManager == nullptr)
			return GENERALERROR;

		uint64 targetid = creature->getTargetID();
		ManagedReference<SceneObject*> sceneO = playerManager->getInRangeStructureWithAdminRights(creature, targetid);

		if (sceneO == nullptr || (!sceneO->isStructureObject() && !sceneO->isPobShip())) {
			creature->sendSystemMessage("@player_structure:no_building"); //You must be in a building, be near an installation, or have one targeted to do that.
			return INVALIDTARGET;
		}

		auto zoneServer = server->getZoneServer();

		if (zoneServer == nullptr)
			return GENERALERROR;

		String targetName, listName, action;

		try {
			UnicodeTokenizer tokenizer(arguments);
			tokenizer.getStringToken(targetName);
			tokenizer.getStringToken(listName);
			tokenizer.getStringToken(action);

			listName = listName.toUpperCase();
			action = action.toLowerCase();

			if (action != "remove" && action != "add" && action != "toggle")
				throw Exception();

		} catch (Exception& e) {
			return INVALIDPARAMETERS;
		}

		// info(true) << " Target Name: " << targetName << " List Name: " << listName << " Action: " << action;

		if (targetName.length() > 40) {
			creature->sendSystemMessage("@player_structure:permission_40_char"); //Permission list entries cannot be longer than 40 characters.
			return INVALIDPARAMETERS;
		}

		int ret = 1;

		if (sceneO->isPobShip()) {
			ret = handlePobShipPermissions(creature, sceneO, targetName, listName, action, arguments.toString());
		} else if (sceneO->isStructureObject()) {
			ret = handleStructurePermissions(creature, sceneO, targetName, listName, action, arguments.toString());
		}

		return ret;
	}

	int handleStructurePermissions(CreatureObject* creature, SceneObject* sceneO, String targetName, String listName, String action, String arguments) const {
		if (creature == nullptr || sceneO == nullptr)
			return GENERALERROR;

		StructureObject* structureObject = cast<StructureObject*>(sceneO);

		if (structureObject == nullptr)
			return GENERALERROR;

		ZoneServer* zoneServer = server->getZoneServer();

		if (zoneServer == nullptr)
			return GENERALERROR;

		ManagedReference<GuildManager*> guildManager = zoneServer->getGuildManager();

		if (guildManager == nullptr)
			return GENERALERROR;

		ManagedReference<PlayerManager*> playerManager = server->getPlayerManager();

		if (playerManager == nullptr)
			return GENERALERROR;

		Locker _lock(structureObject, creature);

		if (!structureObject->hasPermissionList(listName)) {
			creature->sendSystemMessage("@player_structure:must_specify_list"); // You must specify a valid permission list (Entry, Ban, Admin, Hopper)
			return INVALIDPARAMETERS;
		}

		if (targetName.beginsWith("account:")) {
			if (listName != "ADMIN") {
				creature->sendSystemMessage("Account entries are supported only on the structure Admin list.");
				return INVALIDPARAMETERS;
			}

			String characterName = targetName.subString(8);
			if (characterName.isEmpty()) {
				creature->sendSystemMessage("That account character does not exist.");
				return INVALIDPARAMETERS;
			}

			uint32 savedAccountID = structureObject->getAccountAdminID(characterName);
			ManagedReference<CreatureObject*> accountCharacter = nullptr;
			Reference<Account*> account = nullptr;
			if (savedAccountID != 0 && action != "add")
				account = AccountManager::getAccount(savedAccountID);
			else if (!playerManager->existsName(characterName)) {
				creature->sendSystemMessage("Character " + characterName + " does not exist.");
				return INVALIDPARAMETERS;
			} else {
				accountCharacter = playerManager->getPlayer(characterName);
				if (accountCharacter != nullptr && accountCharacter->getPlayerObject() != nullptr)
					account = accountCharacter->getPlayerObject()->getAccount();
			}
			if (account == nullptr) {
				creature->sendSystemMessage("Could not load the account for " + characterName + ".");
				return INVALIDPARAMETERS;
			}

			uint32 accountID = account->getAccountID();
			bool listed = structureObject->isAccountAdmin(accountID);
			bool sameEntry = savedAccountID == accountID;
			if (listed && !sameEntry) {
				creature->sendSystemMessage("This account is already on the Admin list under a different character name.");
				return INVALIDPARAMETERS;
			}
			bool removing = action == "remove" || (action == "toggle" && sameEntry);
			if (removing && !listed) {
				creature->sendSystemMessage("That account is not on the Admin list.");
				return INVALIDPARAMETERS;
			}
			if (!removing && listed) {
				creature->sendSystemMessage("That account is already on the Admin list.");
				return INVALIDPARAMETERS;
			}
			if (accountCharacter != nullptr && structureObject->isOwnedByAccount(accountCharacter)) {
				creature->sendSystemMessage("The owning account already has structure access.");
				return INVALIDPARAMETERS;
			}
			PlayerObject* actorGhost = creature->getPlayerObject();
			if (removing && actorGhost != nullptr && actorGhost->getAccountID() == accountID) {
				creature->sendSystemMessage("You cannot remove your own account from the Admin list.");
				return INVALIDPARAMETERS;
			}

			Reference<CharacterList*> characters = account->getCharacterList();
			if (characters == nullptr)
				return GENERALERROR;
			characters->update();
			for (int i = 0; i < characters->size(); ++i) {
				const CharacterListEntry& entry = characters->get(i);
				if (entry.getGalaxyID() == zoneServer->getGalaxyID() && !removing && structureObject->isOnBanList(entry.getObjectID())) {
					creature->sendSystemMessage(entry.getFirstName() + " is banned from this structure. Remove the ban first.");
					return INVALIDPARAMETERS;
				}
			}

			Vector<uint64> individualEntries;
			if (!removing) {
				for (int i = 0; i < characters->size(); ++i) {
					const CharacterListEntry& entry = characters->get(i);
					if (entry.getGalaxyID() == zoneServer->getGalaxyID() && structureObject->isOnPermissionList("ADMIN", entry.getObjectID())) {
						individualEntries.add(entry.getObjectID());
						structureObject->revokePermission("ADMIN", entry.getObjectID());
					}
				}
			}
			int result = removing ? structureObject->revokeAccountAdmin(accountID) : structureObject->grantAccountAdmin(accountID, characterName);
			if (result != (removing ? StructurePermissionList::REVOKED : StructurePermissionList::GRANTED)) {
				for (int i = 0; i < individualEntries.size(); ++i)
					structureObject->grantPermission("ADMIN", individualEntries.get(i));
				creature->sendSystemMessage("Could not change the account Admin entry; check the list capacity.");
				return INVALIDPARAMETERS;
			}

			TransactionLog trx(creature, accountCharacter != nullptr ? accountCharacter.get() : creature, structureObject, TrxCode::PERMISSIONLIST);
			trx.addState("permissionAction", removing ? "remove" : "add");
			trx.addState("permissionList", "admin");
			trx.addState("permissionTarget", targetName);
			trx.addState("permissionAccountID", accountID);
			if (structureObject->isBuildingObject()) {
				for (int i = 0; i < characters->size(); ++i) {
					const CharacterListEntry& entry = characters->get(i);
					if (entry.getGalaxyID() != zoneServer->getGalaxyID())
						continue;
					ManagedReference<CreatureObject*> member = zoneServer->getObject(entry.getObjectID()).castTo<CreatureObject*>();
					if (member != nullptr)
						cast<BuildingObject*>(structureObject)->updateCellPermissionsTo(member);
				}
			}
			creature->sendSystemMessage(targetName + (removing ? " removed from" : " added to") + " the Admin list.");
			return SUCCESS;
		}

		ManagedReference<SceneObject*> targetObject = nullptr;

		if (targetName.beginsWith("guild:")) {
			String abbrev = targetName.replaceAll("guild:","");

			if (abbrev == "" || !guildManager->guildAbbrevExists(abbrev)) {
				creature->sendSystemMessage("That guild does not exist.");
				return INVALIDPARAMETERS;
			}

			targetObject = guildManager->getGuildFromAbbrev(abbrev);

		} else {
			if (!playerManager->existsName(targetName)) {
				StringIdChatParameter params("@player_structure:modify_list_invalid_player"); // %NO is an invalid player name.
				params.setTO(targetName);

				creature->sendSystemMessage(params);
				return INVALIDPARAMETERS;
			}

			targetObject = playerManager->getPlayer(targetName);
		}

		if (targetObject == nullptr || (!targetObject->isPlayerCreature() && !targetObject->isGuildObject())) {
			return INVALIDPARAMETERS;
		}

		uint64 targetID = targetObject->getObjectID();

		if (structureObject->isPermissionListFull(listName)) {
			if (action == "add" || (action == "toggle" && !structureObject->isOnPermissionList(listName, targetID))) {
				creature->sendSystemMessage("@player_structure:too_many_entries"); // You have too many entries on that list. You must remove some before adding more.
				return INVALIDPARAMETERS;
			}
		}

		if (action == "add" && structureObject->isOnPermissionList(listName, targetID)) {
			creature->sendSystemMessage("That name is already on that list.");
			return INVALIDPARAMETERS;
		}

		bool isOwner = structureObject->isOwnerOf(creature->getObjectID());
		bool isTargetOwner = structureObject->isOwnerOf(targetID);

		if (structureObject->isOnBanList(targetID)) {
			if (listName == "ENTRY" || listName == "ADMIN") {
				creature->sendSystemMessage("@player_structure:no_banned"); //You cannot add a banned player to the entry list.
				return INVALIDPARAMETERS;
			} else if (listName != "BAN") {
				StringIdChatParameter params("@player_structure:cannot_add_banned"); //%NO must first be removed from the banned list.
				params.setTO(targetName);
				creature->sendSystemMessage(params);
				return INVALIDPARAMETERS;
			}

		} else if (structureObject->isOnAdminList(targetID)) {
			if (listName == "BAN" && isTargetOwner) {
				creature->sendSystemMessage("You cannot ban the owner.");
				return INVALIDPARAMETERS; //Can't ban the owner.
			}

			if (creature->getObjectID() == targetID) {
				if (listName == "VENDOR") {
					creature->sendSystemMessage("You cannot be added to the vendor list when you are already on the admin list for this structure.");
				} else {
					creature->sendSystemMessage("@player_structure:cannot_remove_self"); // You cannot remove yourself from the admin list.
				}

				return INVALIDPARAMETERS;
			}

			if (listName == "ENTRY" && !isOwner) {
				creature->sendSystemMessage("@player_structure:no_remove_admin"); //You cannot remove an admin from the entry list.
				return INVALIDPARAMETERS;
			}

			if (listName == "ADMIN" && isTargetOwner) {
				creature->sendSystemMessage("@player_structure:cannot_remove_owner"); //You cannot remove the owner from the admin list.
				return INVALIDPARAMETERS;
			}

			if (listName == "HOPPER" && !isOwner) {
				creature->sendSystemMessage("@player_structure:hopper_cannot_remove_admin"); //You cannot remove an admin from the hopper list.
				return INVALIDPARAMETERS;
			}
		}

		if (listName == "BAN" && !structureObject->isOnBanList(targetID)) {
			structureObject->revokeAllPermissions(targetID); //Remove all existing permissions
		}

		StringIdChatParameter params;
		params.setTO(targetName);

		TransactionLog trx(creature, targetObject, structureObject, TrxCode::PERMISSIONLIST);

		if (trx.isVerbose()) {
			// Include extra details
			trx.addState("commandCreature", creature->getObjectID());
			trx.addState("commandArguments", arguments);
			trx.addRelatedObject(targetObject->getObjectID());
		}

		int returnCode = StructurePermissionList::LISTNOTFOUND;

		if (action == "add")
			returnCode = structureObject->grantPermission(listName, targetID);
		else if (action == "remove")
			returnCode = structureObject->revokePermission(listName, targetID);
		else
			returnCode = structureObject->togglePermission(listName, targetID);

		trx.addState("permissionAction", action);
		trx.addState("permissionList", listName.toLowerCase());
		trx.addState("permissionTarget", targetName);

		switch (returnCode) {
		case StructurePermissionList::GRANTED:
			trx.addState("permissionResult", "granted");
			params.setStringId("@player_structure:player_added"); //%NO added to the list.
			break;
		case StructurePermissionList::REVOKED:
			trx.addState("permissionResult", "revoked");
			params.setStringId("@player_structure:player_removed"); //%NO removed from the list.
			break;
		default:
			trx.addState("permissionResult", "failed");
			trx.abort() << "Permission change failed with code: " << returnCode;
			return GENERALERROR;
		}

		creature->sendSystemMessage(params);

		if (targetObject->isPlayerCreature()) {
			ManagedReference<CreatureObject*> targetPlayer = cast<CreatureObject*>(targetObject.get());

			//Update the cell permissions in case the player is in the building currently.
			if (targetPlayer != nullptr && structureObject->isBuildingObject()) {
				BuildingObject* buildingObject = cast<BuildingObject*>( structureObject);
				buildingObject->updateCellPermissionsTo(targetPlayer);
			}
		} else {
			ManagedReference<GuildObject*> targetGuild = cast<GuildObject*>(targetObject.get());

			// Update the cell permissions to nearby guild members
			if (targetGuild != nullptr && structureObject->isBuildingObject()) {
				ManagedReference<BuildingObject*> buildingObject = cast<BuildingObject*>(structureObject);

				if (buildingObject != nullptr) {
					GuildStructurePermissionsTask* guildStructTask = new GuildStructurePermissionsTask(buildingObject, targetGuild);

					if (guildStructTask != nullptr)
						guildStructTask->execute();
				}
			}
		}

		return SUCCESS;
	}

	int handlePobShipPermissions(CreatureObject* creature, SceneObject* sceneO, String targetName, String listName, String action, String arguments) const {
		if (creature == nullptr || sceneO == nullptr)
			return GENERALERROR;

		PobShipObject* pobShip = sceneO->asPobShip();

		if (pobShip == nullptr)
			return GENERALERROR;

		ZoneServer* zoneServer = server->getZoneServer();

		if (zoneServer == nullptr)
			return GENERALERROR;

		ManagedReference<GuildManager*> guildManager = zoneServer->getGuildManager();

		if (guildManager == nullptr)
			return GENERALERROR;

		ManagedReference<PlayerManager*> playerManager = server->getPlayerManager();

		if (playerManager == nullptr)
			return GENERALERROR;

		Locker _lock(pobShip, creature);

		if (!pobShip->hasPermissionList(listName)) {
			creature->sendSystemMessage("@player_structure:must_specify_list"); //You must specify a valid permission list (Entry, Ban, Admin, Hopper)
			return INVALIDPARAMETERS;
		}

		CreatureObject* owner = pobShip->getOwner().get();

		if (owner == nullptr)
			return GENERALERROR;

		ManagedReference<SceneObject*> targetObject = nullptr;

		if (targetName.beginsWith("guild:")) {
			String abbrev = targetName.replaceAll("guild:","");

			if (abbrev == "" || !guildManager->guildAbbrevExists(abbrev)) {
				creature->sendSystemMessage("That guild does not exist.");
				return INVALIDPARAMETERS;
			}

			targetObject = guildManager->getGuildFromAbbrev(abbrev);

		} else {
			if (!playerManager->existsName(targetName)) {
				StringIdChatParameter params("@player_structure:modify_list_invalid_player"); //%NO is an invalid player name.
				params.setTO(targetName);

				creature->sendSystemMessage(params);
				return INVALIDPARAMETERS;
			}

			targetObject = playerManager->getPlayer(targetName);
		}

		if (targetObject == nullptr || (!targetObject->isPlayerCreature() && !targetObject->isGuildObject())) {
			return INVALIDPARAMETERS;
		}

		uint64 targetID = targetObject->getObjectID();
		bool isOnPermsList = pobShip->isOnPermissionList(listName, targetID);

		if (pobShip->isPermissionListFull(listName)) {
			if (action == "add" || (action == "toggle" && !isOnPermsList)) {
				creature->sendSystemMessage("@player_structure:too_many_entries"); //You have too many entries on that list. You must remove some before adding more.
				return INVALIDPARAMETERS;
			}
		}

		if (action == "add" && isOnPermsList) {
			creature->sendSystemMessage("That name is already on that list.");
			return INVALIDPARAMETERS;
		}


		if (creature->getObjectID() == targetID) {
			creature->sendSystemMessage("@player_structure:cannot_remove_self"); //You cannot remove yourself from the admin list.
			return INVALIDPARAMETERS;
		}

		if (listName == "ADMIN" && owner->getObjectID() == targetObject->getObjectID() && (action.contains("toggle") || action.contains("remove"))) {
			creature->sendSystemMessage("@player_structure:cannot_remove_owner"); //You cannot remove the owner from the admin list.
			return INVALIDPARAMETERS;
		}

		StringIdChatParameter params;
		params.setTO(targetName);

		TransactionLog trx(creature, targetObject, pobShip, TrxCode::PERMISSIONLIST);

		if (trx.isVerbose()) {
			// Include extra details
			trx.addState("commandCreature", creature->getObjectID());
			trx.addState("commandArguments", arguments);
			trx.addRelatedObject(targetObject->getObjectID());
		}

		int returnCode = StructurePermissionList::LISTNOTFOUND;

		if (action == "add")
			returnCode = pobShip->grantPermission(listName, targetID);
		else if (action == "remove")
			returnCode = pobShip->revokePermission(listName, targetID);
		else
			returnCode = pobShip->togglePermission(listName, targetID);

		trx.addState("permissionAction", action);
		trx.addState("permissionList", listName.toLowerCase());
		trx.addState("permissionTarget", targetName);

		switch (returnCode) {
		case StructurePermissionList::GRANTED:
			trx.addState("permissionResult", "granted");
			params.setStringId("@player_structure:player_added"); //%NO added to the list.
			break;
		case StructurePermissionList::REVOKED:
			trx.addState("permissionResult", "revoked");
			params.setStringId("@player_structure:player_removed"); //%NO removed from the list.
			break;
		default:
			trx.addState("permissionResult", "failed");
			trx.abort() << "Permission change failed with code: " << returnCode;
			return GENERALERROR;
		}

		creature->sendSystemMessage(params);

		if (targetObject->isPlayerCreature()) {
			ManagedReference<CreatureObject*> targetPlayer = cast<CreatureObject*>(targetObject.get());

			//Update the cell permissions in case the player is in the building currently.
			if (targetPlayer != nullptr) {
				pobShip->updateCellPermissionsTo(targetPlayer);
			}
		} else {
			ManagedReference<GuildObject*> targetGuild = cast<GuildObject*>(targetObject.get());

			//Update the cell permissions to guild members.
			if (targetGuild != nullptr) {

				for (int i = 0; i < targetGuild->getTotalMembers(); ++i) {
					uint64 memberID = targetGuild->getMember(i);
					ManagedReference<CreatureObject*> guildMember = zoneServer->getObject(memberID).castTo<CreatureObject*>();

					if (guildMember != nullptr)
						pobShip->updateCellPermissionsTo(guildMember);
				}
			}
		}

		return SUCCESS;
	}
};

#endif //PERMISSIONLISTMODIFYCOMMAND_H_
