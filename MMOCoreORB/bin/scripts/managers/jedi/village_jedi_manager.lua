JediManager = require("managers.jedi.jedi_manager")
local Logger = require("utils.logger")
local QuestManager = require("managers.quest.quest_manager")

jediManagerName = "VillageJediManager"

NOTINABUILDING = 0

NUMBEROFTREESTOMASTER = 6

VillageJediManager = JediManager:new {
	screenplayName = jediManagerName,
	jediManagerName = jediManagerName,
	jediProgressionType = VILLAGEJEDIPROGRESSION,
	startingEvent = nil,
}

-- Handling of the useItem event.
-- @param pSceneObject pointer to the item object.
-- @param itemType the type of item that is used.
-- @param pPlayer pointer to the creature object that used the item.
function VillageJediManager:useItem(pSceneObject, itemType, pPlayer)
	if (pSceneObject == nil or pPlayer == nil) then
		return
	end

	Logger:log("useItem called with item type " .. itemType, LT_INFO)
	if itemType == ITEMHOLOCRON then
		VillageJediManagerHolocron.useHolocron(pSceneObject, pPlayer)
	end
	if itemType == ITEMWAYPOINTDATAPAD then
		SithShadowEncounter:useWaypointDatapad(pSceneObject, pPlayer)
	end
	if itemType == ITEMTHEATERDATAPAD then
		SithShadowIntroTheater:useTheaterDatapad(pSceneObject, pPlayer)
	end
end

-- Handling of the checkForceStatus command.
-- @param pPlayer pointer to the creature object of the player who performed the command
function VillageJediManager:checkForceStatusCommand(pPlayer)
	if (pPlayer == nil) then
		return
	end

	Glowing:checkForceStatusCommand(pPlayer)
end

-- Handling of the onPlayerLoggedIn event. The progression of the player will be checked and observers will be registered.
-- @param pPlayer pointer to the creature object of the player who logged in.
function VillageJediManager:onPlayerLoggedIn(pPlayer)
	if (pPlayer == nil) then
		return
	end

	Glowing:onPlayerLoggedIn(pPlayer)

	if (VillageJediManagerCommon.isVillageEligible(pPlayer) and not CreatureObject(pPlayer):hasSkill("force_title_jedi_novice")) then
		awardSkill(pPlayer, "force_title_jedi_novice")
	end

	if (FsIntro:isOnIntro(pPlayer)) then
		FsIntro:onLoggedIn(pPlayer)
	end

	if (FsOutro:isOnOutro(pPlayer)) then
		FsOutro:onLoggedIn(pPlayer)
	end

	FsPhase1:onLoggedIn(pPlayer)
	FsPhase2:onLoggedIn(pPlayer)
	FsPhase3:onLoggedIn(pPlayer)
	FsPhase4:onLoggedIn(pPlayer)

	if (not VillageCommunityCrafting:isOnActiveCrafterList(pPlayer)) then
		VillageCommunityCrafting:removeSchematics(pPlayer, 2)
		VillageCommunityCrafting:removeSchematics(pPlayer, 3)
	end

	JediTrials:onPlayerLoggedIn(pPlayer)
end

function VillageJediManager:onPlayerLoggedOut(pPlayer)
	if (pPlayer == nil) then
		return
	end

	if (FsIntro:isOnIntro(pPlayer)) then
		FsIntro:onLoggedOut(pPlayer)
	end

	if (FsOutro:isOnOutro(pPlayer)) then
		FsOutro:onLoggedOut(pPlayer)
	end

	FsPhase1:onLoggedOut(pPlayer)
	FsPhase2:onLoggedOut(pPlayer)
	FsPhase3:onLoggedOut(pPlayer)
end

--Check for force skill prerequisites
function VillageJediManager:canLearnSkill(pPlayer, skillName)
	if string.find(skillName, "force_sensitive") ~= nil then
		local index = string.find(skillName, "0")
		if index ~= nil then
			local skillNameFinal = string.sub(skillName, 1, string.len(skillName) - 3)
			if CreatureObject(pPlayer):getScreenPlayState("VillageUnlockScreenPlay:" .. skillNameFinal) < 2 then
				return false
			end
		end
	end

	if skillName == "force_title_jedi_rank_01" and CreatureObject(pPlayer):getForceSensitiveSkillCount(false) < 24 then
		return false
	end

	if skillName == "force_title_jedi_rank_03" and not CreatureObject(pPlayer):villageKnightPrereqsMet("") then
		return false
	end

	return true
end

--Check to ensure force skill prerequisites are maintained
function VillageJediManager:canSurrenderSkill(pPlayer, skillName)

	if skillName == "force_title_jedi_rank_02" or skillName == "force_title_jedi_novice" then
		CreatureObject(pPlayer):sendSystemMessage("@jedi_spam:revoke_force_title")
		return false
	end

	if string.find(skillName, "force_sensitive_") and CreatureObject(pPlayer):hasSkill("force_title_jedi_rank_02") and CreatureObject(pPlayer):getForceSensitiveSkillCount(false) <= 24 then
		CreatureObject(pPlayer):sendSystemMessage("@jedi_spam:revoke_force_sensitive")
		return false
	end

	if string.find(skillName, "force_discipline_") and CreatureObject(pPlayer):hasSkill("force_title_jedi_rank_03") and not CreatureObject(pPlayer):villageKnightPrereqsMet(skillName) then
		return false
	end

	return true
end

-- Simulate the complete ordered plan so cumulative prerequisite failures are
-- caught before any skill is removed. Keep this check free of player messages.
function VillageJediManager:canSurrenderSkills(pPlayer, skillNames, ownedSkillNames)
	if pPlayer == nil then
		return false
	end

	local owned = {}
	local forceSensitiveCount = 0
	local jediPoints = 0
	local fullTrees = 0
	local skillManager = LuaSkillManager()

	for skillName in string.gmatch(ownedSkillNames, "%S+") do
		local pSkill = skillManager:getSkill(skillName)
		if pSkill == nil then
			return false
		end

		owned[skillName] = LuaSkill(pSkill):getSkillPointsRequired()
		if string.find(skillName, "force_sensitive", 1, true) and string.find(skillName, "0", 1, true) then
			forceSensitiveCount = forceSensitiveCount + 1
		end

		if string.find(skillName, "force_discipline_", 1, true) and
			(string.find(skillName, "0", 1, true) or string.find(skillName, "novice", 1, true) or string.find(skillName, "master", 1, true)) then
			jediPoints = jediPoints + owned[skillName]
			if string.find(skillName, "4", 1, true) then
				fullTrees = fullTrees + 1
			end
		end
	end

	for skillName in string.gmatch(skillNames, "%S+") do
		local points = owned[skillName]
		if points == nil then
			return false
		end

		if skillName == "force_title_jedi_rank_02" or skillName == "force_title_jedi_novice" then
			return false
		end

		local forceSensitive = string.find(skillName, "force_sensitive_", 1, true)
		local forceDiscipline = string.find(skillName, "force_discipline_", 1, true)
		local completeTree = string.find(skillName, "4", 1, true) ~= nil

		-- The existing single-skill rule also blocks novice/master removal when
		-- the remaining tier-box count has reached 24, even though they cost no tier box.
		if forceSensitive and owned["force_title_jedi_rank_02"] ~= nil and forceSensitiveCount <= 24 then
			return false
		end

		if forceDiscipline and owned["force_title_jedi_rank_03"] ~= nil and
			(jediPoints - points < 206 or fullTrees - (completeTree and 1 or 0) < 2) then
			return false
		end

		owned[skillName] = nil
		if string.find(skillName, "force_sensitive", 1, true) and string.find(skillName, "0", 1, true) then
			forceSensitiveCount = forceSensitiveCount - 1
		end

		if forceDiscipline and
			(string.find(skillName, "0", 1, true) or string.find(skillName, "novice", 1, true) or string.find(skillName, "master", 1, true)) then
			jediPoints = jediPoints - points
			if completeTree then
				fullTrees = fullTrees - 1
			end
		end
	end

	return true
end

-- Handling of the onFSTreesCompleted event.
-- @param pPlayer pointer to the creature object of the player
function VillageJediManager:onFSTreeCompleted(pPlayer, branch)
	if (pPlayer == nil) then
		return
	end

	if (QuestManager.hasCompletedQuest(pPlayer, QuestManager.quests.OLD_MAN_FINAL) or VillageJediManagerCommon.hasJediProgressionScreenPlayState(pPlayer, VILLAGE_JEDI_PROGRESSION_COMPLETED_VILLAGE) or VillageJediManagerCommon.hasJediProgressionScreenPlayState(pPlayer, VILLAGE_JEDI_PROGRESSION_DEFEATED_MELLIACHAE)) then
		return
	end

	if (VillageJediManagerCommon.getLearnedForceSensitiveBranches(pPlayer) >= NUMBEROFTREESTOMASTER) then
		VillageJediManagerCommon.setJediProgressionScreenPlayState(pPlayer, VILLAGE_JEDI_PROGRESSION_COMPLETED_VILLAGE)
		FsOutro:startOldMan(pPlayer)
	end
end

function VillageJediManager:onSkillRevoked(pPlayer, pSkill)
	if (pPlayer == nil) then
		return
	end

	if (JediTrials:isOnPadawanTrials(pPlayer) or JediTrials:isOnKnightTrials(pPlayer)) then
		JediTrials:droppedSkillDuringTrials(pPlayer, pSkill)
	end
end

registerScreenPlay("VillageJediManager", true)

return VillageJediManager
