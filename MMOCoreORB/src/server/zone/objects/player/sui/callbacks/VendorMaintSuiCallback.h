/*
 * VendorMaintSuiCallback.h
 *
 *  Created on: Feb 5, 2012
 *      Author: Kyle
 */

#ifndef VENDORMAINTCALLBACK_H_
#define VENDORMAINTCALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/tangible/components/vendor/VendorDataComponent.h"

class VendorMaintSuiCallback : public SuiCallback {

public:
	VendorMaintSuiCallback(ZoneServer* serv) : SuiCallback(serv) {

	}

	void run(CreatureObject* creature, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		bool cancelPressed = (eventIndex == 1);

		if (!sui->isInputBox() || creature == nullptr || cancelPressed || args->size() <= 0) {
			return;
		}

		try {
			int value = Integer::valueOf(args->get(0).toString());

			ManagedReference<SceneObject*> vendor = sui->getUsingObject().get();

			if(vendor == nullptr)
				return;

			DataObjectComponentReference* data = vendor->getDataObjectComponent();
			if(data == nullptr || data->get() == nullptr || !data->get()->isVendorData()) {
				return;
			}

			VendorDataComponent* vendorData = cast<VendorDataComponent*>(data->get());
			if(vendorData == nullptr) {
				return;
			}

			if (vendorData->getOwnerId() != creature->getObjectID())
				return;

			if (sui->getWindowType() == SuiWindowType::STRUCTURE_VENDOR_SKIM) {
				if (!creature->hasSkill("crafting_merchant_master")) {
					vendorData->setSkimPercent(0);
					return;
				}
				if (value < 0 || value > 100) {
					creature->sendSystemMessage("Vendor skim must be between 0 and 100 percent.");
					return;
				}
				vendorData->setSkimPercent(value);
				creature->sendSystemMessage("Vendor skim set to " + String::valueOf(value) + "%.");
			} else if(sui->getWindowType() == SuiWindowType::STRUCTURE_VENDOR_PAY) {
				vendorData->handlePayMaintanence(value);
			} else if (sui->getWindowType() == SuiWindowType::STRUCTURE_VENDOR_WITHDRAW) {
				vendorData->handleWithdrawMaintanence(value);
			}


		} catch(Exception& e) {

		}
	}
};

#endif /* VENDORMAINTCALLBACK_H_ */
