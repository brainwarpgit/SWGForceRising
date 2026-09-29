/*
 * PlaceStructureSessionImplementation.cpp
 *
 *  Created on: Jun 13, 2011
 *      Author: crush
 */

#include "server/zone/objects/player/sessions/PlaceStructureSession.h"
#include "server/chat/ChatManager.h"
#include "server/zone/managers/structure/StructureManager.h"
#include "server/zone/managers/structure/tasks/StructureConstructionCompleteTask.h"
#include "server/zone/managers/object/ObjectManager.h"
#include "server/zone/objects/area/ActiveArea.h"
#include "server/zone/objects/building/BuildingObject.h"
#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/PlayerObject.h"
#include "server/zone/objects/structure/StructureObject.h"
#include "server/zone/objects/tangible/deed/structure/StructureDeed.h"
#include "templates/tangible/SharedStructureObjectTemplate.h"
#include "server/zone/objects/area/areashapes/CircularAreaShape.h"
#include "server/zone/objects/transaction/TransactionLog.h"
#include "server/zone/Zone.h"
#include "server/zone/managers/gcw/GCWManager.h"

void PlaceStructureSessionImplementation::initializeTransientMembers() {
	FacadeImplementation::initializeTransientMembers();
	// A restored session must never release a token from a new server process.
	lotReservation = 0;
}

int PlaceStructureSessionImplementation::constructStructure(float x, float y, int angle) {
	ManagedReference<StructureDeed*> deed = deedObject.get();
	ManagedReference<Zone*> thisZone = zone.get();
	ManagedReference<CreatureObject*> creature = creatureObject.get();

	if (deed == nullptr || thisZone == nullptr || creature == nullptr) {
		cancelSession();
		return 1;
	}

	positionX = x;
	positionY = y;
	directionAngle = angle;

	TemplateManager* templateManager = TemplateManager::instance();

	String serverTemplatePath = deed->getGeneratedObjectTemplate();
	Reference<const SharedStructureObjectTemplate*> serverTemplate = dynamic_cast<SharedStructureObjectTemplate*>(templateManager->getTemplate(serverTemplatePath.hashCode()));

	if (serverTemplate == nullptr || temporaryNoBuildZone.get() != nullptr || lotReservation != 0) {
		cancelSession();
		return 1;
	}

	auto ghost = creature->getPlayerObject();
	int lots = serverTemplate->getLotSize();
	lotReservation = StructureManager::instance()->reserveAccountLots(ghost, lots);

	if (lotReservation == 0) {
		StringIdChatParameter params("@player_structure:not_enough_lots");
		params.setDI(lots);
		creature->sendSystemMessage(params);
		cancelSession();
		return 1;
	}

	try {
		placeTemporaryNoBuildZone(serverTemplate);

		if (temporaryNoBuildZone.get() == nullptr) {
			cancelSession();
			return 1;
		}

		String barricadeServerTemplatePath = serverTemplate->getConstructionMarkerTemplate();
		int constructionDuration = 100; //Set the duration for 100ms as a fall back if it doesn't have a barricade template.

		if (!barricadeServerTemplatePath.isEmpty()) {
			ManagedReference<SceneObject*> barricade = ObjectManager::instance()->createObject(barricadeServerTemplatePath.hashCode(), 0, "");

			if (barricade != nullptr) {
				constructionBarricade = barricade;
				barricade->initializePosition(x, 0, y); //The construction barricades are always at the terrain height.

				const StructureFootprint* structureFootprint = serverTemplate->getStructureFootprint();

				if (structureFootprint != nullptr && (structureFootprint->getRowSize() > structureFootprint->getColSize())) {
					angle = angle + 180;
				}

				barricade->rotate(angle); //All construction barricades need to be rotated 180 degrees for some reason.

				Locker tLocker(barricade);

				if (!thisZone->transferObject(barricade, -1, true)) {
					tLocker.release();
					cancelSession();
					return 1;
				}

				constructionDuration = lots * 3000; //3 seconds per lot.

				if (serverTemplatePath.contains("faction_perk")) {
					GCWManager* gcwMan = thisZone->getGCWManager();

					if (gcwMan != nullptr) {
						constructionDuration = gcwMan->getBasePlacementDelay() * 1000;
					}
				}
			}
		}

		Reference<Task*> task = new StructureConstructionCompleteTask(creature, _this.getReferenceUnsafeStaticCast());
		task->schedule(constructionDuration);
	} catch (...) {
		cancelSession();
		throw;
	}

	return 0;
}

void PlaceStructureSessionImplementation::placeTemporaryNoBuildZone(const SharedStructureObjectTemplate* serverTemplate) {
	ManagedReference<Zone*> thisZone = zone.get();

	if (thisZone == nullptr)
		return;

	Reference<const StructureFootprint*> structureFootprint = serverTemplate->getStructureFootprint();

	//float temporaryNoBuildZoneWidth = structureFootprint->getLength() + structureFootprint->getWidth();

	ManagedReference<CircularAreaShape*> areaShape = new CircularAreaShape();

	Locker alocker(areaShape);

	// Guild halls are approximately 55 m long, 64 m radius will surely cover that in all directions.
	// Even if the placement coordinate aren't in the center of the building.
	areaShape->setRadius(64);
	areaShape->setAreaCenter(positionX, positionY);

	ManagedReference<ActiveArea*> noBuildZone = (thisZone->getZoneServer()->createObject(STRING_HASHCODE("object/active_area.iff"), 0)).castTo<ActiveArea*>();

	if (noBuildZone == nullptr)
		return;

	Locker locker(noBuildZone);
	temporaryNoBuildZone = noBuildZone;

	noBuildZone->initializePosition(positionX, 0, positionY);
	noBuildZone->setAreaShape(areaShape);
	noBuildZone->addAreaFlag(ActiveArea::NOBUILDZONEAREA);

	if (!thisZone->transferObject(noBuildZone, -1, true)) {
		temporaryNoBuildZone = nullptr;
		noBuildZone->destroyObjectFromWorld(true);
	}
}

void PlaceStructureSessionImplementation::removeTemporaryNoBuildZone() {
	ManagedReference<ActiveArea*> noBuildZone = temporaryNoBuildZone.get();
	temporaryNoBuildZone = nullptr;

	if (noBuildZone != nullptr) {
		Locker locker(noBuildZone);

		noBuildZone->destroyObjectFromWorld(true);
	}
}

int PlaceStructureSessionImplementation::completeSession() {
	ManagedReference<StructureDeed*> deed = deedObject.get();
	ManagedReference<CreatureObject*> creature = creatureObject.get();
	ManagedReference<Zone*> thisZone = zone.get();

	if (deed == nullptr || creature == nullptr || thisZone == nullptr || lotReservation == 0)
		return cancelSession();

	auto activeSession = creature->getActiveSession(SessionFacadeType::PLACESTRUCTURE).castTo<PlaceStructureSession*>();

	if (activeSession != _this.getReferenceUnsafeStaticCast() || creature->getZone() != thisZone)
		return cancelSession();

	if (!deed->isPersistent() || deed->getParent() != nullptr || deed->getZone() != nullptr)
		return cancelSession();

	String serverTemplatePath = deed->getGeneratedObjectTemplate();

	StructureManager* structureManager = StructureManager::instance();
	ManagedReference<StructureObject*> structureObject;

	try {
		structureObject = structureManager->placeStructure(creature, serverTemplatePath, positionX, positionY, directionAngle, 1, lotReservation);
	} catch (...) {
		cancelSession();
		throw;
	}

	TransactionLog trx(deed, creature, structureObject, TrxCode::STRUCTUREDEED);
	trx.addState("subjectTemplate", serverTemplatePath);

	if (structureObject == nullptr)
		return cancelSession();

	{
		Locker locker(structureObject, creature);
		structureObject->setDeedObjectID(deed->getObjectID());
	}

	// The structure owns the deed now; cleanup must never return it to inventory.
	deedObject = nullptr;
	cancelSession();

	Locker clocker(structureObject, creature);
	deed->notifyStructurePlaced(creature, structureObject);

	ManagedReference<PlayerObject*> ghost = creature->getPlayerObject();

	if (ghost != nullptr) {

		//Create Waypoint
		ManagedReference<WaypointObject*> waypointObject = ( thisZone->getZoneServer()->createObject(STRING_HASHCODE("object/waypoint/world_waypoint_blue.iff"), 1)).castTo<WaypointObject*>();

		Locker locker(waypointObject);

		waypointObject->setCustomObjectName(structureObject->getDisplayedName(), false);
		waypointObject->setActive(true);
		waypointObject->setPosition(positionX, 0, positionY);
		waypointObject->setPlanetCRC(thisZone->getZoneCRC());
		structureObject->setWaypointID(waypointObject->getObjectID());

		ghost->addWaypoint(waypointObject, false, true);

		locker.release();

		//Create an email.
		ManagedReference<ChatManager*> chatManager = thisZone->getZoneServer()->getChatManager();

		if (chatManager != nullptr) {
			UnicodeString subject = "@player_structure:construction_complete_subject";

			StringIdChatParameter emailBody("@player_structure:construction_complete");
			emailBody.setTO(structureObject->getObjectName());
			emailBody.setDI(ghost->getLotsRemaining());

			chatManager->sendMail("@player_structure:construction_complete_sender", subject, emailBody, creature->getFirstName(), waypointObject);
		}

		if (structureObject->isBuildingObject()) {
			BuildingObject* building = cast<BuildingObject*>(structureObject.get());

			if (building->getSignObject() != nullptr) {
				if (building->isCivicStructure() || building->isCommercialStructure())
					building->setCustomObjectName(structureObject->getDisplayedName(), true);
				else
					building->setCustomObjectName(creature->getFirstName() + "'s House", true);
			}
		}
	}

	return 0;
}

int PlaceStructureSessionImplementation::cancelSession() {
	ManagedReference<CreatureObject*> creature = creatureObject.get();
	ManagedReference<StructureDeed*> deed = deedObject.get();
	ManagedReference<SceneObject*> barricade = constructionBarricade.get();
	uint64 reservation = lotReservation;

	// Clear each handle before cleanup so cancellation can safely be repeated.
	lotReservation = 0;
	deedObject = nullptr;
	constructionBarricade = nullptr;

	if (reservation != 0)
		StructureManager::instance()->releaseAccountLots(reservation);

	if (barricade != nullptr) {
		Locker locker(barricade);
		barricade->destroyObjectFromWorld(true);
	}

	removeTemporaryNoBuildZone();

	if (creature != nullptr) {
		if (deed != nullptr) {
			Locker locker(deed, creature);

			// A transferred or deleted deed is no longer ours to restore.
			if (deed->isPersistent() && deed->getParent() == nullptr && deed->getZone() == nullptr) {
				auto inventory = creature->getSlottedObject("inventory");

				if (inventory == nullptr || !inventory->transferObject(deed, -1, true, true))
					error("Unable to return the deed after cancelling structure placement.");
			}
		}

		auto activeSession = creature->getActiveSession(SessionFacadeType::PLACESTRUCTURE).castTo<PlaceStructureSession*>();

		if (activeSession == _this.getReferenceUnsafeStaticCast())
			creature->dropActiveSession(SessionFacadeType::PLACESTRUCTURE);
	}

	return 0;
}
