#ifndef STRUCTUREFINDITEMRESULTSUICALLBACK_H_
#define STRUCTUREFINDITEMRESULTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/managers/structure/StructureManager.h"

class StructureFindItemResultSuiCallback : public SuiCallback {
	String keyword;

public:
	StructureFindItemResultSuiCallback(ZoneServer* server, const String& keyword) : SuiCallback(server), keyword(keyword) {}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (!sui->isListBox() || eventIndex == 1 || args == nullptr || args->size() < 1)
			return;

		auto object = sui->getUsingObject().get();
		if (object == nullptr || !object->isBuildingObject())
			return;

		auto list = cast<SuiListBox*>(sui);
		int index = Integer::valueOf(args->get(0).toString());
		if (index < 0 || index >= list->getMenuSize())
			return;

		StructureManager::instance()->moveStructureItemTo(player, cast<StructureObject*>(object.get()), list->getMenuObjectID(index), keyword);
	}
};

#endif
