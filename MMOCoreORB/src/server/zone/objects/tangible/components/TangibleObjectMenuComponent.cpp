/*
 * TangibleObjectMenuComponent.cpp
 *
 *  Created on: 26/05/2011
 *      Author: victor
 */

#include "TangibleObjectMenuComponent.h"
#include "server/zone/objects/player/sessions/SlicingSession.h"
#include "server/zone/packets/object/ObjectMenuResponse.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/player/sui/colorbox/SuiColorBox.h"
#include "server/zone/objects/player/sui/callbacks/ColorArmorSuiCallback.h"
#include "server/zone/objects/tangible/components/WearableColorOptions.h"

void TangibleObjectMenuComponent::fillObjectMenuResponse(SceneObject* sceneObject, ObjectMenuResponse* menuResponse, CreatureObject* player) const {
	ObjectMenuComponent::fillObjectMenuResponse(sceneObject, menuResponse, player);

	uint32 gameObjectType = sceneObject->getGameObjectType();

	if (!sceneObject->isTangibleObject())
		return;

	TangibleObject* tano = cast<TangibleObject*>( sceneObject);
	if (WearableColorOptions::canChange(sceneObject, player)) {
		Vector<String> palettes;
		WearableColorOptions::getPalettes(sceneObject, palettes);
		if (palettes.size() > 0) {
			menuResponse->addRadialMenuItem(WearableColorOptions::COLOR_CHANGE, 3, "Color Change");
			if (palettes.size() > 1) {
				for (int i = 0; i < palettes.size() && i < WearableColorOptions::MAX_COLOR_CHANNELS; ++i)
					menuResponse->addRadialMenuItemToRadialID(WearableColorOptions::COLOR_CHANGE,
							WearableColorOptions::FIRST_COLOR_CHANNEL + i, 3, "Color " + String::valueOf(i + 1));
			}
		}
	}

	// Figure out what the object is and if its able to be Sliced.
	if(tano->isSliceable() && !tano->isSecurityTerminal()) { // Check to see if the player has the correct skill level

		bool hasSkill = true;
		ManagedReference<SceneObject*> inventory = player->getSlottedObject("inventory");

		if ((gameObjectType == SceneObjectType::PLAYERLOOTCRATE) && !player->hasSkill("combat_smuggler_novice"))
			hasSkill = false;
		else if (sceneObject->isContainerObject())
			hasSkill = false; // Let the container handle our slice menu
		else if (sceneObject->isMissionTerminal() && !player->hasSkill("combat_smuggler_slicing_01"))
			hasSkill = false;
		else if (sceneObject->isWeaponObject() && (!inventory->hasObjectInContainer(sceneObject->getObjectID()) || !player->hasSkill("combat_smuggler_slicing_02")))
			hasSkill = false;
		else if (sceneObject->isArmorObject() && (!inventory->hasObjectInContainer(sceneObject->getObjectID()) || !player->hasSkill("combat_smuggler_slicing_03")))
			hasSkill = false;

		if(hasSkill)
			menuResponse->addRadialMenuItem(69, 3, "@slicing/slicing:slice"); // Slice
	}

	if (player->getPlayerObject() != nullptr && player->getPlayerObject()->isPrivileged()) {
		/// Viewing components used to craft item, for admins
		ManagedReference<SceneObject*> container = tano->getSlottedObject("crafted_components");

		if (container != nullptr && container->getContainerObjectsSize() > 0) {
			SceneObject* satchel = container->getContainerObject(0);

			if (satchel != nullptr && satchel->getContainerObjectsSize() > 0) {
				menuResponse->addRadialMenuItem(79, 3, "@ui_radial:ship_manage_components"); // View Components
			}
		}
	}

	ManagedReference<SceneObject*> parent = tano->getParent().get();
	if (parent != nullptr && parent->getGameObjectType() == SceneObjectType::STATICLOOTCONTAINER) {
		menuResponse->addRadialMenuItem(10, 3, "@ui_radial:item_pickup"); //Pick up
	}
}

int TangibleObjectMenuComponent::handleObjectMenuSelect(SceneObject* sceneObject, CreatureObject* player, byte selectedID) const {
	if (!sceneObject->isTangibleObject())
		return 0;

	if ((selectedID == WearableColorOptions::COLOR_CHANGE ||
			(selectedID >= WearableColorOptions::FIRST_COLOR_CHANNEL &&
			selectedID < WearableColorOptions::FIRST_COLOR_CHANNEL + WearableColorOptions::MAX_COLOR_CHANNELS)) &&
			sceneObject->isWearableObject()) {
		if (!WearableColorOptions::canChange(sceneObject, player))
			return 0;

		Vector<String> palettes;
		WearableColorOptions::getPalettes(sceneObject, palettes);
		if (palettes.size() == 0)
			return 0;

		ManagedReference<PlayerObject*> ghost = player->getPlayerObject();
		ZoneServer* server = player->getZoneServer();
		if (ghost == nullptr || server == nullptr)
			return 0;

		int selected = selectedID == WearableColorOptions::COLOR_CHANGE ? 0 :
			selectedID - WearableColorOptions::FIRST_COLOR_CHANNEL;
		if ((palettes.size() > 1 && selectedID == WearableColorOptions::COLOR_CHANGE) ||
			selected < 0 || selected >= palettes.size() ||
			selected >= WearableColorOptions::MAX_COLOR_CHANNELS)
			return 0;

		ManagedReference<SuiColorBox*> box = new SuiColorBox(player, SuiWindowType::COLOR_ARMOR);
		box->setCallback(new ColorArmorSuiCallback(server));
		box->setColorPalette(palettes.get(selected));
		box->setUsingObject(sceneObject);
		box->setSkillMod(255);
		ghost->addSuiBox(box);
		player->sendMessage(box->generateMessage());
		return 1;
	}

	TangibleObject* tano = cast<TangibleObject*>( sceneObject);


	if (selectedID == 69 && player->hasSkill("combat_smuggler_novice") ) { // Slice [PlayerLootCrate]
		if (player->containsActiveSession(SessionFacadeType::SLICING)) {
			player->sendSystemMessage("@slicing/slicing:already_slicing");
			return 0;
		}

		//Create Session
		ManagedReference<SlicingSession*> session = new SlicingSession(player);
		session->initalizeSlicingMenu(player, tano);

		return 0;
	} else if (selectedID == 79) { // See components (admin)
		if(player->getPlayerObject() != nullptr && player->getPlayerObject()->isPrivileged()) {

			SceneObject* container = tano->getSlottedObject("crafted_components");
			if(container != nullptr) {

				if(container->getContainerObjectsSize() > 0) {

					SceneObject* satchel = container->getContainerObject(0);

					if(satchel != nullptr) {

						satchel->sendWithoutContainerObjectsTo(player);
						satchel->openContainerTo(player);

					} else {
						player->sendSystemMessage("There is no satchel this container");
					}
				} else {
					player->sendSystemMessage("There are no items in this container");
				}
			} else {
				player->sendSystemMessage("There is no component container in this object");
			}
		}

		return 0;
	}else
		return ObjectMenuComponent::handleObjectMenuSelect(sceneObject, player, selectedID);

}
