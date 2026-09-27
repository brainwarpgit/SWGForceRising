/*
				Copyright <SWGEmu>
		See file COPYING for copying conditions.*/

#ifndef SURRENDERSKILLSUICALLBACK_H_
#define SURRENDERSKILLSUICALLBACK_H_

#include "server/zone/managers/skill/SkillManager.h"
#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/SuiWindowType.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"

class SurrenderSkillSuiCallback : public SuiCallback {
	String selection;
	Vector<String> skills;
	bool confirmation;

public:
	SurrenderSkillSuiCallback(ZoneServer* server, const String& selection, const Vector<String>& skills, bool confirmation)
		: SuiCallback(server), selection(selection), skills(skills), confirmation(confirmation) {
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isListBox() || eventIndex != 0)
			return;

		auto skillManager = SkillManager::instance();

		if (skillManager == nullptr)
			return;

		if (confirmation) {
			if (sui->getWindowType() == SuiWindowType::SURRENDER_SKILL_CONFIRM)
				skillManager->confirmSkillSurrender(player, selection, skills);
			return;
		}

		if (sui->getWindowType() != SuiWindowType::SURRENDER_SKILL_SELECT || args == nullptr || args->size() < 1)
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

		skillManager->requestSkillSurrender(player, skills.get(index));
	}
};

#endif /* SURRENDERSKILLSUICALLBACK_H_ */
