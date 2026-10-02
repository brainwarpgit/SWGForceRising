#ifndef STRUCTUREWITHDRAWPOWERSUICALLBACK_H_
#define STRUCTUREWITHDRAWPOWERSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/managers/structure/StructureManager.h"

class StructureWithdrawPowerSuiCallback : public SuiCallback {
public:
	StructureWithdrawPowerSuiCallback(ZoneServer* server) : SuiCallback(server) {}

	void run(CreatureObject* creature, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (creature == nullptr || !sui->isTransferBox() || eventIndex == 1 || args->size() < 2)
			return;
		ManagedReference<SceneObject*> object = sui->getUsingObject().get();
		if (object == nullptr || !object->isInstallationObject())
			return;
		StructureObject* structure = cast<StructureObject*>(object.get());
		if (structure->getZone() == nullptr)
			return;
		int amount = Integer::valueOf(args->get(1).toString());
		Locker locker(structure, creature);
		StructureManager::instance()->withdrawPower(structure, creature, amount);
	}
};

#endif /* STRUCTUREWITHDRAWPOWERSUICALLBACK_H_ */
