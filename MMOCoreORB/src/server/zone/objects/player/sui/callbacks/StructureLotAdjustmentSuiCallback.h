/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef STRUCTURELOTADJUSTMENTSUICALLBACK_H_
#define STRUCTURELOTADJUSTMENTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/managers/structure/StructureManager.h"
#include <limits>

class StructureLotAdjustmentSuiCallback : public SuiCallback {
	uint64 ownerID;
	int additionalLots;
	bool remove;

public:
	StructureLotAdjustmentSuiCallback(ZoneServer* server, uint64 ownerID, int additionalLots, bool remove)
		: SuiCallback(server), ownerID(ownerID), additionalLots(additionalLots), remove(remove) {
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isTransferBox() || eventIndex != 0)
			return;

		// The transfer slider returns the amount moved in its second field.
		const String input = args != nullptr && args->size() > 1 ? args->get(1).toString().trim() : String();
		int64 amount = 0;
		if (!input.isEmpty() && input.length() <= 10) {
			for (int i = 0; i < input.length(); ++i) {
				const char digit = input.charAt(i);
				if (digit < '0' || digit > '9') {
					amount = 0;
					break;
				}
				amount = amount * 10 + (digit - '0');
			}
		}
		if (amount <= 0 || amount > std::numeric_limits<int>::max()) {
			player->sendSystemMessage("Enter a whole number of lots greater than zero.");
			return;
		}

		ManagedReference<SceneObject*> object = sui->getUsingObject().get();
		if (object == nullptr || !object->isStructureObject()) {
			player->sendSystemMessage("The structure is no longer available.");
			return;
		}

		StructureManager::instance()->applyStructureLotAdjustment(player, cast<StructureObject*>(object.get()),
				remove, static_cast<int>(amount), ownerID, additionalLots);
	}
};

#endif // STRUCTURELOTADJUSTMENTSUICALLBACK_H_
