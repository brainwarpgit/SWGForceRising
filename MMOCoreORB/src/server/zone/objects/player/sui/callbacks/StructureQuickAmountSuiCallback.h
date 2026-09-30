#ifndef STRUCTUREQUICKAMOUNTSUICALLBACK_H_
#define STRUCTUREQUICKAMOUNTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/structure/StructureObject.h"

class StructureQuickAmountSuiCallback : public SuiCallback {
	bool power;

public:
	StructureQuickAmountSuiCallback(ZoneServer* server, bool power) : SuiCallback(server), power(power) {}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (!sui->isInputBox() || eventIndex == 1 || args->size() < 1)
			return;

		String input = args->get(0).toString();
		if (input.isEmpty() || input.length() > 9)
			return;
		for (int i = 0; i < input.length(); ++i) {
			if (input.charAt(i) < '0' || input.charAt(i) > '9') {
				player->sendSystemMessage("Enter a whole number from 0 to 100,000,000.");
				return;
			}
		}

		int64 amount = Long::valueOf(input);
		if (amount < 0 || amount > 100000000) {
			player->sendSystemMessage("Enter a whole number from 0 to 100,000,000.");
			return;
		}

		ManagedReference<SceneObject*> object = sui->getUsingObject().get();
		if (object == nullptr || !object->isStructureObject())
			return;
		StructureObject* structure = cast<StructureObject*>(object.get());
		Locker locker(structure, player);
		if (structure->getZone() == nullptr || !structure->isOwnedByAccount(player)
				|| (power && (!structure->isInstallationObject() || structure->isGeneratorObject())))
			return;

		if (power)
			structure->setQuickPowerAmount((int)amount);
		else
			structure->setQuickMaintenanceAmount((int)amount);
		structure->updateToDatabase();
		player->sendSystemMessage(power ? "Quick power amount saved for this structure." : "Quick maintenance amount saved for this structure.");
	}
};

#endif
