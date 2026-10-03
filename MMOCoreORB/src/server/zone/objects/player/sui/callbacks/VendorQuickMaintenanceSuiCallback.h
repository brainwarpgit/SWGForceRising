#ifndef VENDORQUICKMAINTENANCESUICALLBACK_H_
#define VENDORQUICKMAINTENANCESUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/tangible/components/vendor/VendorDataComponent.h"
#include "server/zone/objects/scene/components/DataObjectComponentReference.h"

class VendorQuickMaintenanceSuiCallback : public SuiCallback {
public:
	VendorQuickMaintenanceSuiCallback(ZoneServer* server) : SuiCallback(server) {}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isInputBox() || eventIndex == 1 || args == nullptr || args->size() < 1)
			return;

		String input = args->get(0).toString();
		if (input.isEmpty() || input.length() > 6) {
			player->sendSystemMessage("Enter a whole number from 0 to 100,000.");
			return;
		}
		for (int i = 0; i < input.length(); ++i) {
			if (input.charAt(i) < '0' || input.charAt(i) > '9') {
				player->sendSystemMessage("Enter a whole number from 0 to 100,000.");
				return;
			}
		}

		int amount = Integer::valueOf(input);
		if (amount > 100000) {
			player->sendSystemMessage("Enter a whole number from 0 to 100,000.");
			return;
		}

		ManagedReference<SceneObject*> vendor = sui->getUsingObject().get();
		if (vendor == nullptr || !vendor->isVendor() || vendor->getZone() == nullptr || !vendor->isInRange(player, 8.f))
			return;

		Locker locker(vendor, player);
		DataObjectComponentReference* data = vendor->getDataObjectComponent();
		if (data == nullptr || data->get() == nullptr || !data->get()->isVendorData())
			return;

		VendorDataComponent* vendorData = cast<VendorDataComponent*>(data->get());
		if (vendorData == nullptr || !vendorData->isInitialized() || !vendorData->isVendorOwner(player))
			return;

		vendorData->setQuickMaintenanceAmount(amount);
		vendor->updateToDatabase();
		player->sendSystemMessage(amount == 0 ? "Quick Maintenance disabled for this vendor." : "Quick Maintenance amount saved for this vendor.");
	}
};

#endif
