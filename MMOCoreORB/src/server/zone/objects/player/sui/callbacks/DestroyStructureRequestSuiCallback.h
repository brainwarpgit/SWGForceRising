/*
 * DestroyStructureRequestSuiCallback.h
 *
 *  Created on: Jun 22, 2011
 *      Author: crush
 */

#ifndef DESTROYSTRUCTUREREQUESTSUICALLBACK_H_
#define DESTROYSTRUCTUREREQUESTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sessions/DestroyStructureSession.h"
#include "server/zone/objects/player/PlayerObject.h"

class DestroyStructureRequestSuiCallback : public SuiCallback {
	ManagedWeakReference<DestroyStructureSession*> destroySession;

public:
	DestroyStructureRequestSuiCallback(ZoneServer* serv, DestroyStructureSession* session) : SuiCallback(serv), destroySession(session) {
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr)
			return;

		bool cancelPressed = (eventIndex == 1);

		ManagedReference<DestroyStructureSession*> session = player->getActiveSession(SessionFacadeType::DESTROYSTRUCTURE).castTo<DestroyStructureSession*>();

		if (session == nullptr || session != destroySession.get())
			return;

		ManagedReference<SceneObject*> usingObject = sui->getUsingObject().get();
		if (usingObject == nullptr || usingObject != session->getStructureObject())
			return;

		if (cancelPressed) {
			session->cancelSession();
			return;
		}

		PlayerObject* ghost = player->getPlayerObject();
		if (ghost != nullptr && !ghost->isStructureDestroyCodeEnabled())
			session->destroyStructure();
		else
			session->sendDestroyCode();
	}
};

#endif /* DESTROYSTRUCTUREREQUESTSUICALLBACK_H_ */
