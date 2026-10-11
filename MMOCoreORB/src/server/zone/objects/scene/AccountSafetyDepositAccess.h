#ifndef ACCOUNTSAFETYDEPOSITACCESS_H_
#define ACCOUNTSAFETYDEPOSITACCESS_H_

#include "server/login/account/Account.h"
#include "server/zone/ZoneServer.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/scene/SceneObject.h"

class AccountSafetyDepositAccess {
public:
	static SceneObject* getRoot(SceneObject* object) {
		if (object == nullptr)
			return nullptr;

		ManagedReference<SceneObject*> root = object->getRootParent();
		SceneObject* candidate = root != nullptr ? root.get() : object;
		return candidate->getParent().get() == nullptr &&
				candidate->getServerObjectCRC() == STRING_HASHCODE("object/tangible/bank/account_bank.iff") ? candidate : nullptr;
	}

	static bool canAccess(SceneObject* object, CreatureObject* creature) {
		SceneObject* root = getRoot(object);
		if (root == nullptr || creature == nullptr || creature->getZone() == nullptr || !creature->isNearBank())
			return false;

		PlayerObject* ghost = creature->getPlayerObject();
		ZoneServer* server = creature->getZoneServer();
		ManagedReference<Account*> account = ghost != nullptr ? ghost->getAccount() : nullptr;
		return account != nullptr && server != nullptr &&
				account->getAccountSafetyDepositID(server->getGalaxyID()) == root->getObjectID();
	}
};

#endif
