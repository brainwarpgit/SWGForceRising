/*
 * DisconnectClientEvent.h
 *
 *  Created on: Oct 14, 2010
 *      Author: oru
 */

#ifndef DISCONNECTCLIENTEVENT_H_
#define DISCONNECTCLIENTEVENT_H_

#include "server/zone/objects/player/PlayerObject.h"
#include "server/login/account/Account.h"
#include "server/zone/ZoneServer.h"
#include "server/zone/CloseObjectsVector.h"
#ifdef WITH_SWGREALMS_API
#include "server/login/SWGRealmsAPI.h"
#endif // WITH_SWGREALMS_API

class DisconnectClientEvent : public Task {
	ManagedReference<CreatureObject*> player;
	ManagedReference<ZoneClientSession*> client;
	int eventType;

public:
	const static int DISCONNECT = 1;
	const static int LOGOUT = 2;
	const static int SETLINKDEAD = 3;

public:
	DisconnectClientEvent(CreatureObject* pl, ZoneClientSession* cl, int type) : Task() {
		player = pl;
		client = cl;
		eventType = type;
	}

	void run() {
		if (player == nullptr || client == nullptr)
			return;

		Locker _locker(player);

		PlayerObject* ghost = player->getPlayerObject();

		if (ghost == nullptr)
			return;

		ManagedReference<Account*> account = ghost->getAccount();
		ZoneServer* zoneServer = player->getZoneServer();
		if (account != nullptr && zoneServer != nullptr) {
			uint64 bankID = account->getAccountSafetyDepositID(zoneServer->getGalaxyID());
			if (bankID != 0) {
				ManagedReference<SceneObject*> bank = zoneServer->getObject(bankID);
				if (bank != nullptr && bank->getCloseObjects() != nullptr) {
					Locker bankLocker(bank, player);
					bank->getCloseObjects()->drop(player.get());
				}
			}
		}

#ifdef WITH_SWGREALMS_API
		String eventTypeStr;

		switch(eventType) {
		case DISCONNECT:
			eventTypeStr = "disconnect";
			break;
		case LOGOUT:
			eventTypeStr = "logout";
			break;
		case SETLINKDEAD:
			eventTypeStr = "setlinkdead";
			break;
		default:
			eventTypeStr = "unknown_" + String::valueOf(eventType);
			break;
		}

		SWGRealmsAPI::instance()->notifyDisconnectClient(client->getIPAddress(), ghost->getAccountID(), player->getObjectID(), eventTypeStr);
#endif // WITH_SWGREALMS_API

		ghost->setLastLogoutWorldPosition();

		switch (eventType) {
		case DISCONNECT:
			ghost->disconnect(false, true);
			break;
		case LOGOUT:
			ghost->logout(true);
			break;
		case SETLINKDEAD:
			ghost->setLinkDead();
			break;
		}
	}


};


#endif /* DISCONNECTCLIENTEVENT_H_ */
