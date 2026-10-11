/*
 * ColorArmorSuiCallback.h
 *
 *  Created on: 2/4/2013
 *      Author: bluree
 *		Credits: TA & Valk
 */

#ifndef COLORARMORSUICALLBACK_H_
#define COLORARMORSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/tangible/components/WearableColorOptions.h"


class ColorArmorSuiCallback : public SuiCallback {
public:
	ColorArmorSuiCallback(ZoneServer* serv) : SuiCallback(serv) {
	}

	void run(CreatureObject* creature, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		bool cancelPressed = (eventIndex == 1);

		if (!sui->isColorPicker() || cancelPressed || args == nullptr || args->size() == 0)
			return;

		if (!creature->isPlayerCreature())
			return;

		SuiColorBox* cBox = cast<SuiColorBox*>(sui);

		int index = Integer::valueOf(args->get(0).toString());
		if (index < 0 || index > 255)
			return;

		String palette = cBox->getColorPalette();

		ManagedReference<SceneObject*> armorRehue = cBox->getUsingObject().get();

		if (armorRehue == nullptr)
			return;
		if (!WearableColorOptions::canChange(armorRehue.get(), creature))
			return;

		Vector<String> palettes;
		WearableColorOptions::getPalettes(armorRehue.get(), palettes);
		bool validPalette = false;
		for (int i = 0; i < palettes.size(); ++i) {
			if (palettes.get(i) == palette) {
				validPalette = true;
				break;
			}
		}
		if (!validPalette)
			return;

		ManagedReference<TangibleObject*> armorRehueTano = armorRehue->asTangibleObject();

		if (armorRehueTano != nullptr) {
			Locker locker(armorRehueTano, creature);

			armorRehueTano->setCustomizationVariable(palette, index, true);
		}
	}
};

#endif /* COLORARMORSUICALLBACK_H_ */
