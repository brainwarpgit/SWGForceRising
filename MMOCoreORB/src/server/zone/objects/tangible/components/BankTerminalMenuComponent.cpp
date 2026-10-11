/*
 * BankTerminalMenuComponent.cpp
 *
 *  Created on: 01/12/2012
 *      Author: Elvaron
 */

#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/login/account/Account.h"
#include "BankTerminalMenuComponent.h"
#include "server/zone/packets/object/ObjectMenuResponse.h"
#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/objects/scene/variables/ContainerPermissions.h"
#include "server/zone/objects/player/sui/banktransferbox/SuiBankTransferBox.h"
#include "server/zone/objects/player/sui/callbacks/BankTerminalSuiCallback.h"
#include "server/zone/Zone.h"
#include "server/zone/ZoneServer.h"
#include "server/zone/CloseObjectsVector.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/transaction/TransactionLog.h"

void BankTerminalMenuComponent::fillObjectMenuResponse(SceneObject* sceneObject, ObjectMenuResponse* menuResponse, CreatureObject* creature) const {
	if (creature == nullptr)
		return;

	menuResponse->addRadialMenuItemToRadialID(20, 68, 3, "@sui:bank_credits"); // Deposit/Withdrawal
	menuResponse->addRadialMenuItemToRadialID(20, 73, 3, "@sui:bank_items"); //Safety Deposit
	menuResponse->addRadialMenuItemToRadialID(20, ACCOUNT_DEPOSIT, 3, "Account Safety Deposit");

	if (creature->getCashCredits() > 0)
		menuResponse->addRadialMenuItemToRadialID(20, 69, 3, "@sui:bank_depositall"); // Deposit all

	if (creature->getBankCredits() > 0)
		menuResponse->addRadialMenuItemToRadialID(20, 70, 3, "@sui:bank_withdrawall"); // Withdraw all

	// Join Bank
	menuResponse->addRadialMenuItemToRadialID(20, 71, 3, "@sui:bank_join");
	// Quit Bank - no checks here since there are error message stfs
	menuResponse->addRadialMenuItemToRadialID(20, 72, 3, "@sui:bank_quit");

	TangibleObjectMenuComponent::fillObjectMenuResponse(sceneObject, menuResponse, creature);
}

int BankTerminalMenuComponent::handleObjectMenuSelect(SceneObject* sceneObject, CreatureObject* creature, byte selectedID) const {
	if (sceneObject == nullptr || creature == nullptr)
		return 0;

	if (!sceneObject->isTangibleObject() || !creature->isPlayerCreature())
		return 0;

	Zone* playerZone = creature->getZone();

	if (playerZone == nullptr)
		return 0;

	ManagedReference<PlayerObject*> ghost = creature->getPlayerObject();

	if (ghost == nullptr)
		return 0;

	String planet = ghost->getBankLocation();

	ManagedReference<CityRegion*> region = sceneObject->getCityRegion().get();

	if (region != nullptr && region->isBanned(creature->getObjectID())) {
		creature->sendSystemMessage("@city/city:youre_city_banned"); // you are banned from this city and may not use any of its public services and structures
		return 0;
	}

	if (selectedID == WITHDRAW || selectedID == 20) {
		ManagedReference<SuiBankTransferBox*> sui = new SuiBankTransferBox(sceneObject, creature, SuiWindowType::BANK_TRANSFER);

		sui->addCash(creature->getCashCredits());
		sui->addBank(creature->getBankCredits());
		sui->setCallback(new BankTerminalSuiCallback(playerZone->getZoneServer()));

		ghost->addSuiBox(sui);
		creature->sendMessage(sui->generateMessage());

		return 0;
	} else if (selectedID == JOIN) {
		if (planet == "") {
			// JOIN BANK
			ghost->setBankLocation(playerZone->getZoneName());

			SceneObject* bank = creature->getSlottedObject("bank");

			if (bank != nullptr) {
				bank->sendTo(creature, true);

				creature->sendSystemMessage("@system_msg:succesfully_joined_bank");
			}
		} else if (planet == playerZone->getZoneName()) {
			// Already joined this bank
			creature->sendSystemMessage("@system_msg:already_member_of_bank");
		} else {
			// Already member different bank
			creature->sendSystemMessage("@system_msg:member_of_different_bank");
		}

		return 0;
	} else if (selectedID == QUIT) {
		SceneObject* bank = creature->getSlottedObject("bank");

		ZoneServer* server = creature->getZoneServer();

		/*It doens't check whether you're on your registered bank's planet
		 * It probably doesn't matter though.
		 * If anyone remembers you had to go to the correct planet for it we can change it */

		if (bank->getContainerObjectsSize() == 0) {
			bank->sendDestroyTo(creature);

			// QUIT BANK
			ghost->setBankLocation("");

			creature->sendSystemMessage("@system_msg:succesfully_quit_bank");
		} else {
			// Not empty
			creature->sendSystemMessage("@system_msg:bank_not_empty");
		}

		return 0;

	} else if (selectedID == DEPOSIT) {
		if (planet == playerZone->getZoneName() || GLOBALSAFETYDEPOSIT) {
			ManagedReference<SceneObject*> bank = creature->getSlottedObject("bank");
			bank->openContainerTo(creature);
		} else {
			creature->sendSystemMessage("@newbie_tutorial/system_messages:bank_info_2");
		}

		return 0;
	} else if (selectedID == ACCOUNT_DEPOSIT) {
		ManagedReference<Account*> account = ghost->getAccount();
		if (account == nullptr || !creature->isNearBank())
			return 0;

		Locker accountLocker(account);
		uint32 galaxyID = playerZone->getZoneServer()->getGalaxyID();
		uint64 bankID = account->getAccountSafetyDepositID(galaxyID);
		ManagedReference<SceneObject*> bank = bankID != 0 ? playerZone->getZoneServer()->getObject(bankID) : nullptr;
		if (bank == nullptr && bankID == 0) {
			bank = playerZone->getZoneServer()->createObject(STRING_HASHCODE("object/tangible/bank/account_bank.iff"), 2);
			if (bank == nullptr) {
				creature->sendSystemMessage("The account safety deposit could not be created. Please try again later.");
				return 0;
			}
			bank->setContainerVolumeLimit(500);
			bank->setCustomObjectName(UnicodeString("Account Safety Deposit"), false);
			ContainerPermissions* permissions = bank->getContainerPermissionsForUpdate();
			permissions->setOwner(0);
			permissions->setInheritPermissionsFromParent(false);
			permissions->setDefaultDenyPermission(ContainerPermissions::OPEN);
			permissions->setDefaultDenyPermission(ContainerPermissions::MOVEIN);
			permissions->setDefaultDenyPermission(ContainerPermissions::MOVEOUT);
			permissions->setDefaultDenyPermission(ContainerPermissions::MOVECONTAINER);
			bank->setZone(playerZone);
			bank->updateToDatabase();
			account->setAccountSafetyDepositID(galaxyID, bank->getObjectID());
		} else if (bank == nullptr) {
			creature->sendSystemMessage("The account safety deposit could not be loaded. Please contact an administrator.");
			return 0;
		}

		Locker bankLocker(bank);
		if (bank->getCloseObjects() == nullptr)
			bank->setCloseObjects(new CloseObjectsVector());
		if (bank->getServerObjectCRC() == STRING_HASHCODE("object/tangible/bank/character_bank.iff")) {
			bank->setServerObjectCRC(STRING_HASHCODE("object/tangible/bank/account_bank.iff"));
			bank->setClientObjectCRC(STRING_HASHCODE("object/tangible/bank/shared_account_bank.iff"));
			bank->setCustomObjectName(UnicodeString("Account Safety Deposit"), false);
			bank->updateToDatabase();
		}
		if (bank->getContainerVolumeLimit() != 500)
			bank->setContainerVolumeLimit(500);
		bank->setZone(playerZone);
		bank->sendTo(creature, true);
		bank->openContainerTo(creature);
		bank->getCloseObjects()->put(creature);
		return 0;
	} else if (selectedID == DEPOSITALL) {
		uint32 cash = creature->getCashCredits();

		StringIdChatParameter params;
		params.setStringId("@base_player:prose_deposit_success");
		params.setDI(cash);
		creature->sendSystemMessage(params);

		TransactionLog trx(creature, creature, TrxCode::BANK, cash, true);
		creature->subtractCashCredits(cash);
		creature->addBankCredits(cash);

		return 0;
	} else if (selectedID == WITHDRAWALL) {
		uint32 cash = creature->getBankCredits();

		StringIdChatParameter params;
		params.setStringId("@base_player:prose_withdraw_success");
		params.setDI(cash);
		creature->sendSystemMessage(params);

		TransactionLog trx(creature, creature, TrxCode::BANK, cash, false);
		creature->subtractBankCredits(cash);
		creature->addCashCredits(cash);

		return 0;
	} else
		return TangibleObjectMenuComponent::handleObjectMenuSelect(sceneObject, creature, selectedID);

	return 0;
}
