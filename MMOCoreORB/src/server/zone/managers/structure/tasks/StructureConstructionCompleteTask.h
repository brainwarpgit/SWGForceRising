/*
 * StructureConstructionCompleteTask.h
 *
 *  Created on: Jun 13, 2011
 *      Author: crush
 */


#ifndef STRUCTURECONSTRUCTIONCOMPLETETASK_H_
#define STRUCTURECONSTRUCTIONCOMPLETETASK_H_

#include "server/zone/objects/creature/CreatureObject.h"
#include "server/zone/objects/player/sessions/PlaceStructureSession.h"

class StructureConstructionCompleteTask : public Task {
	ManagedWeakReference<CreatureObject*> creatureObject;
	ManagedWeakReference<PlaceStructureSession*> placementSession;

public:
	StructureConstructionCompleteTask(CreatureObject* creature, PlaceStructureSession* session) : Task() {
		creatureObject = creature;
		placementSession = session;
	}

	void run() {
		ManagedReference<PlaceStructureSession*> session = placementSession.get();

		if (session == nullptr)
			return;

		ManagedReference<CreatureObject*> creature = creatureObject.get();

		if (creature == nullptr) {
			session->cancelSession();
			return;
		}

		Locker lock(creature);

		auto activeSession = creature->getActiveSession(SessionFacadeType::PLACESTRUCTURE).castTo<PlaceStructureSession*>();

		if (activeSession != session) {
			session->cancelSession();
			return;
		}

		session->completeSession();
	}
};

#endif /*STRUCTURECONSTRUCTIONCOMPLETETASK_H_*/
