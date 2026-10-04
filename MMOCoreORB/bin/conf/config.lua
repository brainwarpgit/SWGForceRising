--Copyright (C) 2007 <SWGEmu>

--This File is part of Core3.

--This program is free software; you can redistribute
--it and/or modify it under the terms of the GNU Lesser
--General Public License as published by the Free Software
--Foundation; either version 2 of the License,
--or (at your option) any later version.

--This program is distributed in the hope that it will be useful,
--but WITHOUT ANY WARRANTY; without even the implied warranty of
--MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
--See the GNU Lesser General Public License for
--more details.

--You should have received a copy of the GNU Lesser General
--Public License along with this program; if not, write to
--the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

--Linking Engine3 statically or dynamically with other modules
--is making a combined work based on Engine3.
--Thus, the terms and conditions of the GNU Lesser General Public License
--cover the whole combination.

--In addition, as a special exception, the copyright holders of Engine3
--give you permission to combine Engine3 program with free software
--programs or libraries that are released under the GNU LGPL and with
--code included in the standard release of Core3 under the GNU LGPL
--license (or modified versions of such code, with unchanged license).
--You may copy and distribute such a system following the terms of the
--GNU LGPL for Engine3 and the licenses of the other code concerned,
--provided that you include the source code of that other code when
--and as the GNU LGPL requires distribution of source code.

--Note that people who make modified versions of Engine3 are not obligated
--to grant this special exception for their modified versions;
--it is their choice whether to do so. The GNU Lesser General Public License
--gives permission to release a modified version without this exception;
--this exception also makes it possible to release a modified version
--which carries forward this exception.

-- Core3 server configuration. Boolean settings use true/false.
-- Nested tables map to dotted source keys (for example, Core3.Login.EnableSessionId).
-- New settings retain source defaults. Commented overrides preserve calculated or
-- context-dependent defaults; uncomment only when an explicit override is wanted.
-- Engine worker/scheduler settings belong in the engine configuration entry points.
-- MOTD and revision strings are loaded from conf/motd.txt and conf/rev.txt.
-- Separate manager Lua files continue to own their own gameplay settings.

Core3 = {

	-- Server services and naming directory
	MakeLogin = true,
	MakeZone = true,
	MakePing = true,
	MakeStatus = true,
	-- Empty uses the local naming directory.
	ORB = "",
	ORBPort = 44419,

	-- Databases
	DBHost = "127.0.0.1",
	DBPort = 3306,
	DBName = "swgemu",
	DBUser = "swgemu",
	DBPass = "123456",
	-- Keep database credentials and this authentication secret private.
	DBSecret = "swgemus3cr37!",
	DBInstances = 2,
	MantisHost = "127.0.0.1",
	MantisPort = 3306,
	MantisName = "swgemu",
	MantisUser = "swgemu",
	MantisPass = "123456",
	-- Mantis table prefix; retain this key spelling for its source reader.
	MantisPrfx = "mantis_",

	-- Login and account policy
	LoginPort = 44453,
	LoginAllowedConnections = 3000,
	-- Login protocol version; the zone client check is PlayerManager.ValidClientVersion.
	LoginRequiredVersion = "20050408-18:00",
	AutoReg = true,
	RegistrationMessage = "Automatic registration is currently disabled. Please contact the administrators of the server in order to get an authorized account.",
	InactiveAccountTitle = "Account Disabled",
	InactiveAccountText = "The server administrators have disabled your account.",
	TermsOfServiceVersion = 0,
	TermsOfService = "",
	Login = {
		API = {
			APIToken = "",
			-- Empty disables external login API integration (requires WITH_SWGREALMS_API).
			BaseURL = "",
			DebugLevel = 0,
			DryRun = false,
			FailOpen = false,
			-- Seconds.
			MetricsInterval = 600,
			-- Leave unset to inherit the global RotateLogSizeMB setting.
			-- RotateLogSizeMB = 100,
			-- Leave unset to derive the stream URL from BaseURL and the galaxy ID.
			-- StreamURL = "",
			-- Seconds.
			Timeout = 30,
			WorkerThreads = 4,
		},
		EnableSessionId = false,
		-- Hours:minutes.
		SessionDuration = "00:15",
	},
	AccountManager = {
		CreatedDateFirstConnect = false,
		HolocronTicketsEnabled = false,
	},

	-- Zone, ping, and status services
	ZoneGalaxyID = 2,
	-- 0 uses the galaxy database port.
	ZoneServerPort = 0,
	-- With USE_RANDOM_EXTRA_PORTS: 1 selects round-robin; other values select random ports.
	ZonePortsBalancer = 1,
	ZoneAllowedConnections = 30000,
	Zone = {
		ThreadsDefault = 1,
	},
	SpaceZone = {
		ThreadsDefault = 1,
	},
	ZoneServer = {
		-- Per-account overrides are also supported by the config API.
		ClientLogLevel = -1,
	},
	PingPort = 44462,
	PingAllowedConnections = 3000,
	StatusPort = 44455,
	StatusAllowedConnections = 500,
	-- Seconds between zone health checks.
	StatusInterval = 30,

	-- Client archives and enabled worlds
	-- Directory containing the server/client TRE archive set.
	TrePath = "/home/swgemu/Desktop/SWGEmu",
	-- First archive wins duplicate paths; keep SWGFR_update_01.tre first.
	TreFiles = {
		"SWGFR_update_01.tre",
		"default_patch.tre",
		"patch_sku1_14_00.tre",
		"patch_14_00.tre",
		"patch_sku1_13_00.tre",
		"patch_13_00.tre",
		"patch_sku1_12_00.tre",
		"patch_12_00.tre",
		"patch_11_03.tre",
		"data_sku1_07.tre",
		"patch_11_02.tre",
		"data_sku1_06.tre",
		"patch_11_01.tre",
		"patch_11_00.tre",
		"data_sku1_05.tre",
		"data_sku1_04.tre",
		"data_sku1_03.tre",
		"data_sku1_02.tre",
		"data_sku1_01.tre",
		"data_sku1_00.tre",
		"patch_10.tre",
		"patch_09.tre",
		"patch_08.tre",
		"patch_07.tre",
		"patch_06.tre",
		"patch_05.tre",
		"patch_04.tre",
		"patch_03.tre",
		"patch_02.tre",
		"patch_01.tre",
		"patch_00.tre",
		"data_other_00.tre",
		"data_static_mesh_01.tre",
		"data_static_mesh_00.tre",
		"data_texture_07.tre",
		"data_texture_06.tre",
		"data_texture_05.tre",
		"data_texture_04.tre",
		"data_texture_03.tre",
		"data_texture_02.tre",
		"data_texture_01.tre",
		"data_texture_00.tre",
		"data_skeletal_mesh_01.tre",
		"data_skeletal_mesh_00.tre",
		"data_animation_00.tre",
		"data_sample_04.tre",
		"data_sample_03.tre",
		"data_sample_02.tre",
		"data_sample_01.tre",
		"data_sample_00.tre",
		"data_music_00.tre",
		"bottom.tre",
	},
	TreManager = {
		-- Repopulate the string database at startup; normally false.
		ReloadStrings = false,
	},
	ZonesEnabled = {
		"corellia",
		"dantooine",
		"dathomir",
		"dungeon1",
		"endor",
		"lok",
		"naboo",
		"rori",
		"talus",
		"tatooine",
		"tutorial",
		"yavin4",
		-------- TEST ZONES -------
		--"09",
		--"10",
		--"11",
		--"character_farm",
		--"cinco_city_test_m5",
		--"creature_test",
		--"endor_asommers",
		--"floratest",
		--"godclient_test",
		--"otoh_gunga",
		--"rivertest",
		--"runtimerules",
		--"simple",
		--"taanab",
		--"test_wearables",
		--"umbra",
		--"watertabletest",
	},
	SpaceZonesEnabled = {
		"space_corellia",
		"space_dantooine",
		"space_dathomir",
		"space_endor",
		"space_heavy1",
		"space_light1",
		"space_lok",
		"space_naboo",
		"space_tatooine",
		"space_yavin4",
		---- TEST ZONES ----
		--"space_09",
		--"space_corellia_2",
		--"space_env",
		--"space_halos",
		--"space_naboo_2",
		--"space_tatooine_2",
	},

	-- Characters and player behavior
	CharacterBuilderEnabled = true,
	-- Maximum expired mail records deleted per cleanup pass.
	CleanupMailCount = 25000,
	-- Minutes between purges of deleted characters (formerly mislabeled DeleteCharacters).
	PurgeDeletedCharacters = 10,
	SameAccountTipsAreFree = false,
	PlayerCreationManager = {
		EnableTutorial = false,
		-- Shared account base lots are this limit times StructureManager.LotsPerCharacter.
		MaxCharactersPerGalaxy = 10,
	},
	PlayerManager = {
		-- Track PvP victims by account; fixes the old missing Core3 namespace.
		AccountVictimList = false,
		AdvancedWaypoints = false,
		DisableGroupVisibility = false,
		GalaxyWideGrouping = false,
		ValidClientVersion = "20050408-18:00",
		WipeFillingOnClone = false,
	},
	PlayerObject = {
		AlwaysSafeLogout = false,
		-- Seconds before unsafe logout after a link loss.
		LinkDeadDelay = 180,
	},

	HelperDroid = {
		-- Master switch for player helpers, including manual calls, help, and quests.
		-- Disabling deletes helpers and their datapad devices on login; quests remain.
		-- Enabling restores missing helpers on login, stored, unless manually deleted.
		Enabled = true,
		-- Recall an existing helper after ground login/travel/zoning.
		-- When false, still call a new helper on the first planet arrival and
		-- when learning Novice Artisan/Brawler/Entertainer/Marksman/Scout/Medic.
		-- These automatic calls keep the existing new-player eligibility rules.
		-- Login replacements stay stored regardless of this setting.
		AutoCallOnZone = true,
	},

	-- Combat, missions, factions, and items
	PvpMode = false,
	JTL = {
		JTLEnabled = false,
	},
	CombatManager = {
		AllowSameAccountLinkDeadBeneficialActions = true,
	},
	MissionManager = {
		AnonymousBountyTerminals = false,
		-- Milliseconds; 48 hours.
		BountyExpirationTime = 172800000,
		IncludeFactionPets = true,
		-- Milliseconds between mission-list requests.
		ListRequestCooldown = 1400,
		MaxBountiesPerJedi = 5,
		-- Optional override; existing mission paths use different true/false defaults.
		-- PlayerBountyCooldown = true,
		-- Milliseconds; 24 hours.
		PlayerBountyCooldownTime = 86400000,
		PrivateStructureJediMissions = true,
	},
	GCWManager = {
		useCovertOvertSystem = false,
	},
	ChatManager = {
		PvpBroadcastChannel = false,
	},
	FrsManager = {
		ImmediateMaintXpDeduction = false,
	},
	LootManager = {
		DebugAttributes = false,
		LootedWearableSockets = false,
	},
	TangibleObject = {
		ForceNoTradeADKMessage = "",
		ForceNoTradeMessage = "",
		NoTradeMessage = "",
	},

	-- Spawns and AI
	Regions = {
		DisableSpaceSpawns = false,
		DisableWorldSpawns = false,
		-- Milliseconds.
		minimumLairSpawnInterval = 5000,
		-- Milliseconds.
		minimumSpaceSpawnInterval = 5000,
		-- Meters beyond the space spawn-area radius.
		spaceSpawnCheckRange = 1024.0,
		-- Meters beyond the ground spawn-area radius.
		spawnCheckRange = 64.0,
	},
	AiAgent = {
		-- Only read in DEBUG_AI builds.
		AiAgentLoadTesting = false,
		-- Leave unset for build defaults: 1 with DEBUG_AI, otherwise 100.
		-- ConsoleThrottle = 100,
		-- Optional override; defaults are WARNING at creation and ERROR after debug reset.
		-- LogLevel = 2,
		Verbose = false,
	},
	-- ShipAiAgent = {
		-- Optional override; defaults are WARNING at creation and ERROR after debug reset.
		-- LogLevel = 2,
	-- },

	-- Structures, travel, and world maintenance
	UnloadContainers = true,
	MaxNavMeshJobs = 6,
	StructureManager = {
		-- Ignore structure template planet lists when placing deeds; other placement rules still apply.
		AllowPlacementOnAllPlanets = false,
		-- Nonnegative integers; negative values are treated as zero.
		-- Storage in buildings with a lot cost: lot cost times ItemsPerLot.
		ItemsPerLot = 100,
		-- Storage in all zero-lot buildings, including civic buildings.
		NoLotItemCount = 400,
		-- Account base lots: MaxCharactersPerGalaxy times this value, plus admin bonus.
		LotsPerCharacter = 10,
		EnhancedFurnitureRotate = false,
	},
	StructureMaintenanceTask = {
		AllowBankPayments = true,
	},
	StructureObject = {
		-- Seconds; the server also adds a randomized delay.
		MaintenanceBootDelay = 600,
	},
	Tweaks = {
		StructureObject = {
			-- Enable orphan-structure removal; false preserves the existing default.
			DestroyOrphans = false,
		},
	},
	ShuttleZoneComponent = {
		-- Milliseconds; five minutes.
		BootDelay = 300000,
	},
	-- PlanetManager = {
		-- Seconds; DEBUG_TRAVEL override. Unset inherits the planet Lua timing.
		-- ShuttleportAwayTime = 300,
		-- Seconds; DEBUG_TRAVEL override. Unset inherits the planet Lua timing.
		-- ShuttleportLandedTime = 120,
		-- Seconds; DEBUG_TRAVEL override. Unset inherits the planet Lua timing.
		-- ShuttleportLandingTime = 11,
		-- Seconds; DEBUG_TRAVEL override. Unset inherits the planet Lua timing.
		-- StarportAwayTime = 60,
		-- Seconds; DEBUG_TRAVEL override. Unset inherits the planet Lua timing.
		-- StarportLandedTime = 120,
		-- Seconds; DEBUG_TRAVEL override. Unset inherits the planet Lua timing.
		-- StarportLandingTime = 14,
	-- },

	-- Logging and diagnostics
	LogFile = "log/core3.log",
	-- Log levels: -1 NONE, 0 FATAL, 1 ERROR, 2 WARNING, 3 LOG, 4 INFO, 5 DEBUG.
	LogFileLevel = 4,
	LogJSON = false,
	-- Flush the main log after each write.
	LogSync = false,
	RotateLogAtStart = false,
	-- Default rotation size inherited by component logs.
	RotateLogSizeMB = 100,
	PlayerLogLevel = 4,
	-- Player log rotation threshold, in lines.
	MaxLogLines = 1000000,
	-- Seconds between online-player log updates.
	OnlineLogSeconds = 300,
	-- Online-player log rotation threshold, in bytes.
	OnlineLogSize = 100000000,
	LogOnlineCount = 3,
	LogOnlineOnSessionChange = true,
	-- Seconds between player session-stat log entries.
	SessionStatsSeconds = 1800,
	LuaLogJSON = false,
	PathfinderLogJSON = false,
	ProgressMonitors = true,
	DumpObjFiles = true,
	LuaEngine = {
		LogLevel = 1,
		LuaEventLogLevel = 4,
	},
	DirectorManager = {
		-- Milliseconds before reporting a slow screenplay load.
		SlowLoadMs = 1000,
	},
	NavMeshManager = {
		LogLevel = 4,
	},
	CommandConfigManager = {
		DumpAdminCommands = false,
	},
	NameManager = {
		FilterTable = "oldFilterWords",
	},

	-- Metrics
	UseMetrics = false,
	MetricsHost = "localhost",
	MetricsPort = 8125,
	MetricsPrefix = "",

	-- Auctions and transaction logging
	MaxAuctionSearchJobs = 1,
	AuctionManager = {
		LogLevel = -1,
		-- Leave unset to inherit the global RotateLogSizeMB setting.
		-- RotateLogSizeMB = 100,
		Startup = {
			ExpireInvalid = false,
		},
	},
	AuctionItem = {
		ExportOnDestroy = false,
	},
	TransactionLog = {
		AsyncExport = false,
		CheckPlayerDebug = true,
		Enabled = false,
		LogLevel = 5,
		PruneCraftedComponents = true,
		PruneCreatureObjects = true,
		-- Leave unset to inherit the global RotateLogSizeMB setting.
		-- RotateLogSizeMB = 100,
		Verbose = false,
		WorkerThreads = 4,
	},

	-- REST API and object exports
	-- 0 disables the REST server.
	RESTServerPort = 0,
	RESTServer = {
		APIToken = "",
		LogLevel = 4,
		-- Leave unset to inherit the global RotateLogSizeMB setting.
		-- RotateLogSizeMB = 100,
		-- Optional TLS certificate path.
		SSLCertFile = "",
		-- Optional TLS private-key path.
		SSLKeyFile = "",
		WorkerThreads = 4,
		-- strftime-style export directory.
		exportDir = "log/exports/api/%Y-%m-%d/%H/",
	},
	SceneObject = {
		-- strftime-style export directory.
		exportDir = "log/exports/%Y-%m-%d/%H/",
	},
}

-- Optional overrides whose keys depend on a zone, command, NPC, or structure name.
-- Existing values are inherited when these overrides are absent.
-- Core3.Zone.ThreadsCorellia = 1
-- Core3.SpaceZone.ThreadsSpaceCorellia = 1
-- Core3.CommandCooldown = { ["commandName"] = 1000 } -- milliseconds
-- Core3.AiAgent["npcTemplateName"] = { LogLevel = 2 }
-- Core3.StructureManager.CreateNavMesh = { ["objectNameFullPath"] = false }

-- conf/config-local.lua runs after config.lua. A Core3 = {...} assignment replaces
-- the entire table; both supplied files therefore contain the complete configuration.
-- Keep local credentials/settings in config-local.lua, which remains ignored by Git.
