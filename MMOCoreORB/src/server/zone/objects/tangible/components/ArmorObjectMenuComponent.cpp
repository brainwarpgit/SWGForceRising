#include "ArmorObjectMenuComponent.h"

void ArmorObjectMenuComponent::fillObjectMenuResponse(SceneObject* sceneObject, ObjectMenuResponse* menuResponse, CreatureObject* player) const {
	WearableObjectMenuComponent::fillObjectMenuResponse(sceneObject, menuResponse, player);
}

int ArmorObjectMenuComponent::handleObjectMenuSelect(SceneObject* sceneObject, CreatureObject* player, byte selectedID) const {
	return WearableObjectMenuComponent::handleObjectMenuSelect(sceneObject, player, selectedID);
}
