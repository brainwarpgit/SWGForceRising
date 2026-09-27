/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef REVOKESKILLSUICALLBACK_H_
#define REVOKESKILLSUICALLBACK_H_

#include "server/zone/managers/skill/SkillManager.h"
#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/SuiWindowType.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"

class RevokeSkillSuiCallback : public SuiCallback {
	uint64 targetID;
	String selection;
	Vector<String> skills;
	bool confirmation;

public:
	RevokeSkillSuiCallback(ZoneServer* server, uint64 targetID, const String& selection, const Vector<String>& skills, bool confirmation)
		: SuiCallback(server), targetID(targetID), selection(selection), skills(skills), confirmation(confirmation) {
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isListBox() || eventIndex != 0)
			return;

		const int expectedWindow = confirmation ? SuiWindowType::REVOKE_SKILL_CONFIRM : SuiWindowType::REVOKE_SKILL_SELECT;

		if (sui->getWindowType() != expectedWindow)
			return;

		auto skillManager = SkillManager::instance();

		if (skillManager == nullptr)
			return;

		if (!skillManager->canRevokeSkills(player)) {
			player->sendSystemMessage("@error_message:insufficient_permissions");
			return;
		}

		if (server == nullptr)
			return;

		ManagedReference<SceneObject*> object = server->getObject(targetID);

		if (object == nullptr || !object->isPlayerCreature() || object->asCreatureObject() == nullptr) {
			player->sendSystemMessage("The player selected for skill revocation is no longer available. No skills were revoked.");
			return;
		}

		CreatureObject* targetCreature = object->asCreatureObject();

		if (confirmation) {
			skillManager->confirmSkillRevocation(player, targetCreature, selection, skills);
			return;
		}

		if (args == nullptr || args->size() < 1)
			return;

		const String indexText = args->get(0).toString();

		if (indexText.isEmpty() || indexText.length() > 9)
			return;

		for (int i = 0; i < indexText.length(); ++i) {
			if (indexText.charAt(i) < '0' || indexText.charAt(i) > '9')
				return;
		}

		const int index = Integer::valueOf(indexText);

		if (index < 0 || index >= skills.size())
			return;

		skillManager->requestSkillRevocation(player, targetCreature, skills.get(index));
	}
};

#endif /* REVOKESKILLSUICALLBACK_H_ */
