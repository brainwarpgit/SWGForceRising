#ifndef STRUCTUREFINDITEMINPUTSUICALLBACK_H_
#define STRUCTUREFINDITEMINPUTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/managers/structure/StructureManager.h"

class StructureFindItemInputSuiCallback : public SuiCallback {
public:
	StructureFindItemInputSuiCallback(ZoneServer* server) : SuiCallback(server) {}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (!sui->isInputBox() || eventIndex == 1 || args == nullptr || args->size() < 1)
			return;

		auto object = sui->getUsingObject().get();
		if (object == nullptr || !object->isBuildingObject())
			return;

		StructureManager::instance()->searchStructureItems(player, cast<StructureObject*>(object.get()), args->get(0).toString());
	}
};

#endif
