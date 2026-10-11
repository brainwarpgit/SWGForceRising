#ifndef CITYTRAINERLISTSUICALLBACK_H_
#define CITYTRAINERLISTSUICALLBACK_H_

#include "server/zone/objects/player/sui/SuiCallback.h"
#include "server/zone/objects/player/sui/listbox/SuiListBox.h"
#include "server/zone/objects/player/sui/messagebox/SuiMessageBox.h"
#include "server/zone/objects/player/sui/callbacks/CityRemoveTrainerSuiCallback.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/region/CityRegion.h"
#include "server/zone/objects/waypoint/WaypointObject.h"
#include "server/zone/objects/scene/SceneObject.h"

using namespace server::zone::objects::region;
using namespace server::zone::objects::creature;
using namespace server::zone::objects::waypoint;

class CityTrainerListSuiCallback : public SuiCallback {
	ManagedWeakReference<CityRegion*> cityRegion;

public:
	CityTrainerListSuiCallback(ZoneServer* server, CityRegion* city) : SuiCallback(server) {
		cityRegion = city;
	}

	void run(CreatureObject* player, SuiBox* sui, uint32 eventIndex, Vector<UnicodeString>* args) {
		if (player == nullptr || sui == nullptr || !sui->isListBox() || eventIndex == 1 || args == nullptr || args->size() < 2)
			return;

		auto city = cityRegion.get();
		auto ghost = player->getPlayerObject();
		if (city == nullptr || ghost == nullptr || (!city->hasMayorAuthority(player) && !ghost->isAdmin()))
			return;

		bool removePressed = Bool::valueOf(args->get(0).toString());
		int index = Integer::valueOf(args->get(1).toString());
		auto list = cast<SuiListBox*>(sui);
		if (index < 0 || index >= list->getMenuSize())
			return;

		uint64 trainerID = list->getMenuObjectID(index);
		if (trainerID == 0)
			return;
		auto trainer = server->getObject(trainerID);
		if (trainer == nullptr || trainer->getZone() == nullptr)
			return;

		Locker cityLock(city, player);
		if (!city->isCitySkillTrainer(trainer))
			return;
		if (removePressed) {
			ManagedReference<SuiMessageBox*> confirm = new SuiMessageBox(player, 0);
			confirm->setPromptTitle("Remove City Trainer");
			confirm->setPromptText("Remove " + trainer->getDisplayedName() + " (object " + String::valueOf(trainerID) + ") from this city and delete it from the world? This cannot be undone.");
			confirm->setCancelButton(true, "@no");
			confirm->setOkButton(true, "@yes");
			confirm->setCallback(new CityRemoveTrainerSuiCallback(server, city, trainerID));
			ghost->addSuiBox(confirm);
			player->sendMessage(confirm->generateMessage());
			return;
		}

		auto waypoint = server->createObject(0xc456e788, 1).castTo<WaypointObject*>();
		if (waypoint == nullptr)
			return;

		auto world = trainer->getWorldPosition();
		Locker waypointLock(waypoint);
		waypoint->setPlanetCRC(trainer->getPlanetCRC());
		waypoint->setPosition(world.getX(), 0.f, world.getY());
		waypoint->setColor(WaypointObject::COLOR_GREEN);
		waypoint->setCustomObjectName(city->getCityRegionName() + " - " + trainer->getDisplayedName(), false);
		waypoint->setActive(true);
		ghost->addWaypoint(waypoint, false, true);
		player->sendSystemMessage("Waypoint created for " + trainer->getDisplayedName() + ".");
	}
};

#endif
