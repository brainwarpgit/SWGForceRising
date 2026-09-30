#ifndef CITYQUICKTREASURYAMOUNTSUICALLBACK_H_
#define CITYQUICKTREASURYAMOUNTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/scene/SceneObject.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/managers/city/CityManager.h"

class CityQuickTreasuryAmountSuiCallback : public SuiCallback {
	ManagedWeakReference<CityRegion*> cityRegion;

public:
	CityQuickTreasuryAmountSuiCallback(ZoneServer* server, CityRegion* city) : SuiCallback(server) {
		cityRegion = city;
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || !sui->isInputBox() || eventIndex == 1 || args->size() < 1)
			return;

		String input = args->get(0).toString();
		if (input.isEmpty() || input.length() > 9) {
			player->sendSystemMessage("Enter a whole number from 0 to 100,000,000.");
			return;
		}
		for (int i = 0; i < input.length(); ++i) {
			if (input.charAt(i) < '0' || input.charAt(i) > '9') {
				player->sendSystemMessage("Enter a whole number from 0 to 100,000,000.");
				return;
			}
		}

		int amount = Integer::valueOf(input);
		if (amount > 100000000) {
			player->sendSystemMessage("Enter a whole number from 0 to 100,000,000.");
			return;
		}

		ManagedReference<CityRegion*> city = cityRegion.get();
		ManagedReference<SceneObject*> terminal = sui->getUsingObject().get();
		if (city == nullptr || terminal == nullptr)
			return;

		server->getCityManager()->setQuickCityTreasuryAmount(city, player, terminal, amount);
	}
};

#endif
