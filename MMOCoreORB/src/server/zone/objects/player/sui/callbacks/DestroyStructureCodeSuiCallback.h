/*
 * DestroyStructureCodeSuiCallback.h
 *
 *  Created on: Jun 22, 2011
 *      Author: crush
 */

#ifndef DESTROYSTRUCTURECODESUICALLBACK_H_
#define DESTROYSTRUCTURECODESUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sessions/DestroyStructureSession.h"


class DestroyStructureCodeSuiCallback : public SuiCallback {
	ManagedWeakReference<DestroyStructureSession*> destroySession;

public:
	DestroyStructureCodeSuiCallback(ZoneServer* serv, DestroyStructureSession* session) : SuiCallback(serv), destroySession(session) {
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

		// Input boxes return the text field followed by the unused combo-box field.
		// Read the text only; malformed responses must also release this session.
		uint32 inputtedCode = 0;
		if (args != nullptr && args->size() > 0) {
			const String codeText = args->get(0).toString();
			if (codeText.length() == 6) {
				for (int i = 0; i < 6; ++i) {
					const char digit = codeText.charAt(i);
					if (digit < '0' || digit > '9') {
						inputtedCode = 0;
						break;
					}
					inputtedCode = inputtedCode * 10 + (digit - '0');
				}
			}
		}

		if (inputtedCode < 100000 || !session->isDestroyCode(inputtedCode)) {
			player->sendSystemMessage("@player_structure:incorrect_destroy_code"); //You have entered an incorrect code. You will have to issue the /destroyStructure again if you wish to continue.
			session->cancelSession();
			return;
		}

		session->destroyStructure();
	}
};

#endif /* DESTROYSTRUCTURECODESUICALLBACK_H_ */
