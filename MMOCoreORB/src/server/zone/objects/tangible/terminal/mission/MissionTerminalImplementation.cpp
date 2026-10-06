/*
 * MissionTerminalImplementation.cpp
 *
 *  Created on: 03/05/11
 *      Author: polonel
 */

#include "server/zone/objects/tangible/terminal/mission/MissionTerminal.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/packets/object/ObjectMenuResponse.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/managers/city/CityManager.h"
#include "server/zone/managers/city/CityRemoveAmenityTask.h"
#include "server/zone/objects/player/sessions/SlicingSession.h"

void MissionTerminalImplementation::fillObjectMenuResponse(ObjectMenuResponse* menuResponse, CreatureObject* player) {
	TerminalImplementation::fillObjectMenuResponse(menuResponse, player);

	ManagedReference<CityRegion*> city = player->getCityRegion().get();

	if (city != nullptr && city->isMayor(player->getObjectID()) && getParent().get() == nullptr) {

		menuResponse->addRadialMenuItem(72, 3, "@city/city:mt_remove"); // Remove

		menuResponse->addRadialMenuItem(73, 3, "@city/city:align"); // Align
		menuResponse->addRadialMenuItemToRadialID(73, 74, 3, "@city/city:north"); // North
		menuResponse->addRadialMenuItemToRadialID(73, 75, 3, "@city/city:east"); // East
		menuResponse->addRadialMenuItemToRadialID(73, 76, 3, "@city/city:south"); // South
		menuResponse->addRadialMenuItemToRadialID(73, 77, 3, "@city/city:west"); // West
	}
}

int MissionTerminalImplementation::handleObjectMenuSelect(CreatureObject* player, byte selectedID) {
	ManagedReference<CityRegion*> city = player->getCityRegion().get();

	if (selectedID == 69 && player->hasSkill("combat_smuggler_slicing_01")) {
		if (isBountyTerminal())
			return 0;

		if (city != nullptr && !city->isClientRegion() && city->isBanned(player->getObjectID())) {
			player->sendSystemMessage("@city/city:banned_services"); // You are banned from using this city's services.
			return 0;
		}

		if (player->containsActiveSession(SessionFacadeType::SLICING)) {
			player->sendSystemMessage("@slicing/slicing:already_slicing");
			return 0;
		}

		if (containsActiveSession(SessionFacadeType::SLICING)) {
			Reference<SlicingSession*> activeSession = getActiveSession(SessionFacadeType::SLICING).castTo<SlicingSession*>();
			if (activeSession != nullptr && player->getGroupID() != 0 && activeSession->getSlicerGroupID() == player->getGroupID())
				player->sendSystemMessage("A group member is already slicing this mission terminal.");
			else
				player->sendSystemMessage("This mission terminal already has an active slicing session.");
			return 0;
		}

		int terminalCooldown = getSliceCooldownRemaining();
		if (terminalCooldown > 0) {
			player->sendSystemMessage("This mission terminal can be sliced again in " + String::valueOf(terminalCooldown) + " seconds.");
			return 0;
		}

		if (!player->checkCooldownRecovery("slicing.terminal")) {
			StringIdChatParameter message;
			message.setStringId("@slicing/slicing:not_yet"); // You will be able to hack the network again in %DI seconds.
			message.setDI(player->getCooldownTime("slicing.terminal")->getTime() - Time().getTime());
			player->sendSystemMessage(message);
			return 0;
		}

		//Create Session
		ManagedReference<SlicingSession*> session = new SlicingSession(player);
		session->initalizeSlicingMenu(player, _this.getReferenceUnsafeStaticCast());

		return 0;

	} else if (selectedID == 72) {

		if (city != nullptr && city->isMayor(player->getObjectID())) {
			CityRemoveAmenityTask* task = new CityRemoveAmenityTask(_this.getReferenceUnsafeStaticCast(), city);
			task->execute();

			player->sendSystemMessage("@city/city:mt_removed"); // The object has been removed from the city.
		}

		return 0;

	} else if (selectedID == 74 || selectedID == 75 || selectedID == 76 || selectedID == 77) {

		CityManager* cityManager = getZoneServer()->getCityManager();
		cityManager->alignAmenity(city, player, _this.getReferenceUnsafeStaticCast(), selectedID - 74);

		return 0;
	}

	return TangibleObjectImplementation::handleObjectMenuSelect(player, selectedID);
}

String MissionTerminalImplementation::getTerminalName() {
	String name = "@terminal_name:terminal_mission";

	if (terminalType == "artisan" || terminalType == "entertainer" || terminalType == "bounty" || terminalType == "imperial" || terminalType == "rebel" || terminalType == "scout")
		name = name + "_" + terminalType;

	return name;
}

void MissionTerminalImplementation::setSliceBonus(CreatureObject* slicer, int percent, int durationSeconds) {
	if (slicer == nullptr)
		return;

	sliceOwnerID = slicer->getObjectID();
	sliceGroupID = slicer->getGroupID();
	sliceBonusPercent = durationSeconds > 0 ? (percent < 0 ? 0 : (percent > 100 ? 100 : percent)) : 0;
	sliceExpiresAt = System::getTime() + (durationSeconds > 0 ? durationSeconds : 0);
	sliceCooldownExpiresAt = sliceExpiresAt + 120; // Two-minute terminal cooldown follows the bonus window.
}

int MissionTerminalImplementation::getSliceCooldownRemaining() {
	int64 remaining = static_cast<int64>(sliceCooldownExpiresAt) - static_cast<int64>(System::getTime());
	return remaining > 0 ? static_cast<int>(remaining) : 0;
}

int MissionTerminalImplementation::getSliceBonusPercent(CreatureObject* player) {
	if (player == nullptr || System::getTime() >= sliceExpiresAt || sliceBonusPercent <= 0 || !player->isInRange(_this.getReferenceUnsafeStaticCast(), 64))
		return 0;

	if (player->getObjectID() == sliceOwnerID || (sliceGroupID != 0 && player->getGroupID() == sliceGroupID))
		return sliceBonusPercent;

	return 0;
}
