#ifndef WEARABLECOLOROPTIONS_H_
#define WEARABLECOLOROPTIONS_H_

#include "conf/ConfigManager.h"
#include "server/zone/objects/building/BuildingObject.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "templates/customization/AssetCustomizationManagerTemplate.h"
#include "templates/params/PaletteColorCustomizationVariable.h"

namespace WearableColorOptions {
	static const byte COLOR_CHANGE = 81;
	static const byte FIRST_COLOR_CHANNEL = 182;
	static const int MAX_COLOR_CHANNELS = 64;

	inline bool canChange(SceneObject* object, CreatureObject* player) {
		if (object == nullptr || player == nullptr || !object->isWearableObject())
			return false;

		ConfigManager* config = ConfigManager::instance();
		if (object->isArmorObject() ? !config->getArmorColorChangeEnabled() : !config->getWearableColorChangeEnabled())
			return false;

		if (object->isASubChildOf(player))
			return true;

		ManagedReference<SceneObject*> parent = object->getParent().get();
		if (parent == nullptr || !parent->isCellObject())
			return false;

		ManagedReference<SceneObject*> building = parent->getParent().get();
		return building != nullptr && building->isBuildingObject() &&
				cast<BuildingObject*>(building.get())->isOnAdminList(player);
	}

	inline void getPalettes(SceneObject* object, Vector<String>& palettes) {
		if (object == nullptr || object->getObjectTemplate() == nullptr)
			return;

		String appearance = object->getObjectTemplate()->getAppearanceFilename();
		VectorMap<String, Reference<CustomizationVariable*> > variables;
		AssetCustomizationManagerTemplate::instance()->getCustomizationVariables(appearance.hashCode(), variables, true);

		for (int i = 0; i < variables.size(); ++i) {
			if (dynamic_cast<PaletteColorCustomizationVariable*>(variables.elementAt(i).getValue().get()) != nullptr)
				palettes.add(variables.elementAt(i).getKey());
		}
	}
}

#endif
