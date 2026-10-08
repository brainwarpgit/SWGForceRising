#ifndef DROIDAUTOLOOTMODULEDATACOMPONENT_H_
#define DROIDAUTOLOOTMODULEDATACOMPONENT_H_

#include "BaseDroidModuleComponent.h"
#include "server/zone/objects/tangible/components/droid/DroidAutoLootObserver.h"

namespace server {
namespace zone {
namespace objects {
namespace tangible {
namespace components {
namespace droid {

class DroidAutoLootModuleDataComponent : public BaseDroidModuleComponent {
protected:
	int creditBonus;
	bool active;
	ManagedReference<DroidAutoLootObserver*> observer;
	Vector<uint64> lootTargets;

public:
	DroidAutoLootModuleDataComponent();
	~DroidAutoLootModuleDataComponent();
	String getModuleName() const;
	void initializeTransientMembers();
	void updateCraftingValues(CraftingValues* values, bool firstUpdate);
	void fillAttributeList(AttributeListMessage* msg, CreatureObject* droid);
	void fillObjectMenuResponse(SceneObject* droidObject, ObjectMenuResponse* menuResponse, CreatureObject* player);
	int handleObjectMenuSelect(CreatureObject* player, byte selectedID, PetControlDevice* controller);
	int getBatteryDrain();
	void onCall();
	void onStore();
	void deactivate(bool onStore = false);
	bool activate();
	bool isActive() const { return active; }
	int getCreditBonus() const { return creditBonus; }
	void addLootTarget(uint64 target, bool first = false) {
		if (target == 0 || lootTargets.contains(target))
			return;
		if (first)
			lootTargets.add(0, target);
		else
			lootTargets.add(target);
	}
	bool hasMoreTargets() const { return lootTargets.size() > 0; }
	uint64 getNextLootTarget() {
		if (lootTargets.size() == 0)
			return 0;
		uint64 target = lootTargets.get(0);
		lootTargets.remove(0);
		return target;
	}
	virtual bool isStackable() { return false; }
	virtual void copy(BaseDroidModuleComponent* other);
};

}
}
}
}
}
}
using namespace server::zone::objects::tangible::components::droid;

#endif
