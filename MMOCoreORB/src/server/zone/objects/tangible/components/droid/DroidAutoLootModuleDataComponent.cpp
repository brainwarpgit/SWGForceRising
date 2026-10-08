#include "DroidAutoLootModuleDataComponent.h"
#include "server/zone/objects/tangible/component/droid/DroidComponent.h"
#include "server/zone/objects/creature/ai/DroidObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/intangible/PetControlDevice.h"
#include "server/zone/managers/creature/PetManager.h"
#include "server/zone/packets/object/ObjectMenuResponse.h"
#include "templates/params/ObserverEventType.h"

DroidAutoLootModuleDataComponent::DroidAutoLootModuleDataComponent() : creditBonus(0), active(false) {
	setLoggingName("DroidAutoLootModule");
}

DroidAutoLootModuleDataComponent::~DroidAutoLootModuleDataComponent() {
}

String DroidAutoLootModuleDataComponent::getModuleName() const {
	return String("auto_loot_module");
}

void DroidAutoLootModuleDataComponent::initializeTransientMembers() {
	DroidComponent* component = cast<DroidComponent*>(getParent());
	if (component == nullptr)
		return;
	creditBonus = component->hasKey("auto_loot_credit_bonus") ?
			Math::max(0, Math::min(15, (int)component->getAttributeValue("auto_loot_credit_bonus"))) : 0;
	if (component->hasKey("auto_loot_active"))
		active = component->getAttributeValue("auto_loot_active") > 0;
	else
		component->addProperty("auto_loot_active", 0.f, 0, "hidden", true);
}

void DroidAutoLootModuleDataComponent::updateCraftingValues(CraftingValues* values, bool firstUpdate) {
	creditBonus = Math::max(0, Math::min(15, (int)values->getCurrentValue("auto_loot_credit_bonus")));
}

void DroidAutoLootModuleDataComponent::fillAttributeList(AttributeListMessage* msg, CreatureObject* droid) {
	msg->insertAttribute("auto_loot_credit_bonus", creditBonus);
	msg->insertAttribute("auto_loot_status", active ? "On" : "Off");
}

void DroidAutoLootModuleDataComponent::fillObjectMenuResponse(SceneObject* droidObject, ObjectMenuResponse* menuResponse, CreatureObject* player) {
	menuResponse->addRadialMenuItem(AUTO_LOOT_MENU, 3, "Auto Loot Options");
	menuResponse->addRadialMenuItemToRadialID(AUTO_LOOT_MENU, AUTO_LOOT_PROGRAM_COMMAND, 3, "Program Target Loot");
	menuResponse->addRadialMenuItemToRadialID(AUTO_LOOT_MENU, AUTO_LOOT_MODULE_TOGGLE, 3, active ? "Disable Auto Loot" : "Enable Auto Loot");
}

int DroidAutoLootModuleDataComponent::handleObjectMenuSelect(CreatureObject* player, byte selectedID, PetControlDevice* controller) {
	if (selectedID == AUTO_LOOT_PROGRAM_COMMAND) {
		if (controller != nullptr) {
			Locker lock(controller);
			controller->setTrainingCommand(PetManager::LOOT);
		}
		return 0;
	}
	if (selectedID != AUTO_LOOT_MODULE_TOGGLE)
		return 0;
	auto droid = getDroidObject();
	if (droid == nullptr || player == nullptr || droid->getLinkedCreature().get() != player)
		return 0;
	Locker dlock(droid, player);
	if (active) {
		deactivate();
		player->sendSystemMessage("Auto Loot disabled.");
	} else if (activate()) {
		player->sendSystemMessage("Auto Loot enabled.");
	}
	DroidComponent* component = cast<DroidComponent*>(getParent());
	if (component != nullptr)
		component->changeAttributeValue("auto_loot_active", active ? 1.f : 0.f);
	return 0;
}

int DroidAutoLootModuleDataComponent::getBatteryDrain() {
	return active ? 4 : 0;
}

void DroidAutoLootModuleDataComponent::deactivate(bool onStore) {
	auto droid = getDroidObject();
	if (droid != nullptr && observer != nullptr) {
		auto owner = droid->getLinkedCreature().get();
		if (owner != nullptr) {
			Locker ownerLock(owner, droid);
			owner->dropObserver(ObserverEventType::KILLEDCREATURE, observer);
		}
	}
	if (!onStore)
		active = false;
	lootTargets.removeAll(0, lootTargets.size());
	if (droid != nullptr && droid->peekBlackboard("autoLootTarget")) {
		droid->eraseBlackboard("autoLootTarget");
		if (!onStore) {
			auto owner = droid->getLinkedCreature().get();
			if (owner != nullptr) {
				droid->setFollowObject(owner);
				droid->storeFollowObject();
				droid->setMovementState(AiAgent::FOLLOWING);
			}
		}
	}
}

bool DroidAutoLootModuleDataComponent::activate() {
	auto droid = getDroidObject();
	if (droid == nullptr || droid->isDead() || droid->isIncapacitated() || !droid->hasPower())
		return false;
	auto owner = droid->getLinkedCreature().get();
	if (owner == nullptr)
		return false;
	if (observer == nullptr) {
		observer = new DroidAutoLootObserver(this);
		observer->deploy();
	}
	Locker ownerLock(owner, droid);
	owner->dropObserver(ObserverEventType::KILLEDCREATURE, observer);
	owner->registerObserver(ObserverEventType::KILLEDCREATURE, observer);
	active = true;
	return true;
}

void DroidAutoLootModuleDataComponent::onCall() {
	if (active)
		activate();
}

void DroidAutoLootModuleDataComponent::onStore() {
	deactivate(true);
}

void DroidAutoLootModuleDataComponent::copy(BaseDroidModuleComponent* other) {
	auto module = cast<DroidAutoLootModuleDataComponent*>(other);
	if (module == nullptr)
		return;
	creditBonus = module->creditBonus;
	DroidComponent* component = cast<DroidComponent*>(getParent());
	if (component != nullptr)
		component->addProperty("auto_loot_credit_bonus", creditBonus, 0, "exp_effectiveness");
}
