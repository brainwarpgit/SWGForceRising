# Core3 configuration audit — 2026-09-27

Status: committed configuration cleanup. Audited the current branch under `MMOCoreORB/src` and `MMOCoreORB/bin`, including ConfigManager wrappers, direct reads, macro-generated transaction flags, dynamic keys, IDL-declared member pointers, and indirect Lua bindings. Separate manager Lua configurations remain separate. Engine3 was not accessed or changed.

## Configuration coverage

Both `bin/conf/config.lua` and the ignored `bin/conf/config-local.lua` now use the same organized layout. Each contains 150 active settings, 15 documented optional settings, and examples for five dynamic key families. There are 92 newly exposed active settings plus the corrected character-purge key; existing settings retain their effective values. Boolean representations are normalized to Lua `true`/`false`.

The user restored the commented TEST-zone options in both files: 17 ground zones and six space zones. These lists match and remain disabled; existing active world lists are unchanged. Lua syntax/evaluation and whitespace checks passed after the additions. Enabling an individual test zone has not been runtime-verified by this audit.

All 150 active keys have production consumers (some require build flags or enabled subsystems). Fifteen settings remain commented because their missing-key behavior inherits another value, varies by call site, or depends on build configuration. Uncommenting those entries intentionally selects an explicit override. No dummy keys or empty configuration tables were added to represent dynamic settings.

## Removed and corrected names

Removed seven entries without production consumers: `MakeWeb`, `WebPorts`, `WebAccessLog`, `WebErrorLog`, `WebSessionTimeout`, `LoginProcessingThreads`, and `ZoneProcessingThreads`. The last two have unused getter definitions, which do not make them active configuration.

- Renamed `DeleteCharacters` to the consumed `PurgeDeletedCharacters` key, retaining its value (minutes).
- Corrected `Core3.Tweaks.StructureObject.DestroyOrphans` in the source reader. The old `DestoryOrphans` spelling remains a fallback only when the corrected key is absent.
- Corrected the victim-list key to `Core3.PlayerManager.AccountVictimList`. The former unprefixed `PlayerManager.accountVictimList` remains a fallback only when the canonical key is absent.
- Corrected ship AI debug reset to read `Core3.ShipAiAgent.LogLevel`, matching ship initialization. Its existing fallback behavior is preserved.
- Kept existing consumed names such as `MantisPrfx`, `exportDir`, and `useCovertOvertSystem`; their casing/abbreviations are part of the supported key names.

Explicit canonical `false` values take precedence over legacy `true` values. Neither compatibility fallback activates a feature by default.

## Keys intentionally kept outside the main configuration

- `Core3.MOTD` and `Core3.Revision` are populated from `conf/motd.txt` and `conf/rev.txt` after Lua parsing. The MOTD getter itself has no production callers.
- `Core3.TreManager.LatestTre` is read only by a test through its wrapper. Its existing ConfigManager default remains `SWGFR_update_01.tre`; the active TRE lists still put that archive first.
- `Core3.JTL.LaunchFromDevice` has an unused wrapper and was not added.
- Engine thread/scheduler variables belong to the engine configuration entry points. Separate resource, crafting, faction, planet, and other manager Lua settings were not moved into Core3.
- Debug-only ConfigManager test values and compatibility aliases are not presented as active settings.

## Dynamic key families

| Family | Configuration example | Missing-key behavior |
| --- | --- | --- |
| Ground-zone threads | `Core3.Zone.ThreadsCorellia` | Inherits `Core3.Zone.ThreadsDefault`. |
| Space-zone threads | `Core3.SpaceZone.ThreadsSpaceCorellia` | Inherits `Core3.SpaceZone.ThreadsDefault`. |
| Command cooldowns | `Core3.CommandCooldown["commandName"]` | Uses that command's cooldown in milliseconds. |
| NPC logging | `Core3.AiAgent["npcTemplateName"].LogLevel` | Retains template/global logging. |
| Structure navigation | `Core3.StructureManager.CreateNavMesh["objectNameFullPath"]` | False; keys use the object name's full string-ID path. |

## Verification

- Executed each configuration in an isolated Lua 5.3 state and compared it with its private original. Every retained value, ordered TRE list, and enabled-world list matched after boolean normalization and the deliberate key rename.
- Verified both files have the same key set and formatting; the pre-existing local differences remain limited to the same six setting names. No local credentials or values are reproduced in this document.
- Reviewed all active keys against production readers, plus commented defaults and the five dynamic families. ConfigManager processes the main file then the local file; the complete local Core3 table replaces the base table, so it includes all settings.
- Checked legacy/canonical boolean precedence for absent, false, and true combinations (18 cases across the two aliases) and preserved the ship logger's reset fallback.
- Whitespace checks passed. No Core3 build or run was performed by the assistant.
- Before commit, verified that the executable updated at `00:48:27` after the edits and includes the corrected key strings. The latest startup loaded both configurations at `00:48:28` and completed at `00:49:08`, with no ERROR/FATAL lines and only the seven known asset warnings. The `00:49:24` online-player snapshot records one player in a world. The user confirmed everything looks good and requested the commit.

No necessary verification remains for this commit. The latest build/startup/login evidence supersedes the earlier pending checks. The orphan-cleanup and account-victim-list switches remain false; their compatibility behavior and ship AI logging reset have static coverage but no dedicated runtime test. Verify those optional paths when used. Commented TEST-zone enablement remains untested.

## Complete key inventory

The source location below identifies a reader or a ConfigManager wrapper with verified production callers. Optional entries appear as commented examples in both configuration files. No configured values or credential defaults are included.

| Key | Type | In config | Reader/wrapper |
| --- | --- | --- | --- |
| `Core3.AccountManager.CreatedDateFirstConnect` | boolean | Active | `MMOCoreORB/src/server/login/account/AccountManager.cpp:412` |
| `Core3.AccountManager.HolocronTicketsEnabled` | boolean | Active | `MMOCoreORB/src/server/zone/packets/ui/CreateTicketMessageCallback.h:26` |
| `Core3.AiAgent.AiAgentLoadTesting` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:689` |
| `Core3.AiAgent.ConsoleThrottle` | integer | Optional | `MMOCoreORB/src/conf/ConfigManager.h:668` |
| `Core3.AiAgent.LogLevel` | integer | Optional | `MMOCoreORB/src/server/zone/objects/creature/ai/AiAgentImplementation.cpp:104` |
| `Core3.AiAgent.Verbose` | boolean | Active | `MMOCoreORB/src/server/zone/objects/creature/ai/bt/Behavior.cpp:27` |
| `Core3.AuctionItem.ExportOnDestroy` | boolean | Active | `MMOCoreORB/src/server/zone/objects/auction/AuctionItemImplementation.cpp:81` |
| `Core3.AuctionManager.LogLevel` | integer | Active | `MMOCoreORB/src/server/zone/managers/auction/AuctionManagerImplementation.cpp:42` |
| `Core3.AuctionManager.RotateLogSizeMB` | integer | Optional | `MMOCoreORB/src/server/zone/managers/auction/AuctionManagerImplementation.cpp:48` |
| `Core3.AuctionManager.Startup.ExpireInvalid` | boolean | Active | `MMOCoreORB/src/server/zone/managers/auction/AuctionManagerImplementation.cpp:440` |
| `Core3.AutoReg` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:474` |
| `Core3.CharacterBuilderEnabled` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:574` |
| `Core3.ChatManager.PvpBroadcastChannel` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:703` |
| `Core3.CleanupMailCount` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:558` |
| `Core3.CombatManager.AllowSameAccountLinkDeadBeneficialActions` | boolean | Active | `MMOCoreORB/src/server/zone/objects/creature/CreatureObjectImplementation.cpp:3849` |
| `Core3.CommandConfigManager.DumpAdminCommands` | boolean | Active | `MMOCoreORB/src/server/zone/managers/objectcontroller/command/CommandConfigManager.cpp:113` |
| `Core3.DBHost` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:330` |
| `Core3.DBInstances` | integer | Active | `MMOCoreORB/src/server/db/ServerDatabase.cpp:25` |
| `Core3.DBName` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:366` |
| `Core3.DBPass` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:374` |
| `Core3.DBPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:362` |
| `Core3.DBSecret` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:378` |
| `Core3.DBUser` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:370` |
| `Core3.DirectorManager.SlowLoadMs` | integer | Active | `MMOCoreORB/src/server/zone/managers/director/DirectorManager.cpp:356` |
| `Core3.DumpObjFiles` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:270` |
| `Core3.FrsManager.ImmediateMaintXpDeduction` | boolean | Active | `MMOCoreORB/src/server/zone/managers/frs/FrsManagerImplementation.cpp:390` |
| `Core3.GCWManager.useCovertOvertSystem` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:716` |
| `Core3.InactiveAccountText` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:570` |
| `Core3.InactiveAccountTitle` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:566` |
| `Core3.JTL.JTLEnabled` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:841` |
| `Core3.LogFile` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:514` |
| `Core3.LogFileLevel` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:518` |
| `Core3.LogJSON` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:542` |
| `Core3.LogOnlineCount` | integer | Active | `MMOCoreORB/src/server/zone/managers/player/OnlineZoneClientMap.h:49` |
| `Core3.LogOnlineOnSessionChange` | boolean | Active | `MMOCoreORB/src/server/zone/managers/player/PlayerManagerImplementation.cpp:223` |
| `Core3.LogSync` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:546` |
| `Core3.Login.API.APIToken` | string | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:144` |
| `Core3.Login.API.BaseURL` | string | Active | `MMOCoreORB/src/server/ServerCore.cpp:725` |
| `Core3.Login.API.DebugLevel` | integer | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:126` |
| `Core3.Login.API.DryRun` | boolean | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:132` |
| `Core3.Login.API.FailOpen` | boolean | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:152` |
| `Core3.Login.API.MetricsInterval` | integer | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:2445` |
| `Core3.Login.API.RotateLogSizeMB` | integer | Optional | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:113` |
| `Core3.Login.API.StreamURL` | string | Optional | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:2510` |
| `Core3.Login.API.Timeout` | integer | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:154` |
| `Core3.Login.API.WorkerThreads` | integer | Active | `MMOCoreORB/src/server/login/SWGRealmsAPI.cpp:122` |
| `Core3.Login.EnableSessionId` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:729` |
| `Core3.Login.SessionDuration` | string | Active | `MMOCoreORB/src/server/login/account/AccountManager.cpp:160` |
| `Core3.LoginAllowedConnections` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:458` |
| `Core3.LoginPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:438` |
| `Core3.LoginRequiredVersion` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:450` |
| `Core3.LootManager.DebugAttributes` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:820` |
| `Core3.LuaEngine.LogLevel` | log-level | Active | `MMOCoreORB/src/server/zone/managers/director/DirectorManager.cpp:417` |
| `Core3.LuaEngine.LuaEventLogLevel` | log-level | Active | `MMOCoreORB/src/server/zone/managers/director/DirectorManager.cpp:334` |
| `Core3.LuaLogJSON` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:550` |
| `Core3.MakeLogin` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:254` |
| `Core3.MakePing` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:262` |
| `Core3.MakeStatus` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:266` |
| `Core3.MakeZone` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:258` |
| `Core3.MantisHost` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:382` |
| `Core3.MantisName` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:398` |
| `Core3.MantisPass` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:406` |
| `Core3.MantisPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:386` |
| `Core3.MantisPrfx` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:410` |
| `Core3.MantisUser` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:402` |
| `Core3.MaxAuctionSearchJobs` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:510` |
| `Core3.MaxLogLines` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:582` |
| `Core3.MaxNavMeshJobs` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:506` |
| `Core3.MetricsHost` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:422` |
| `Core3.MetricsPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:430` |
| `Core3.MetricsPrefix` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:426` |
| `Core3.MissionManager.AnonymousBountyTerminals` | boolean | Active | `MMOCoreORB/src/server/zone/managers/mission/MissionManagerImplementation.cpp:1104` |
| `Core3.MissionManager.BountyExpirationTime` | integer | Active | `MMOCoreORB/src/server/zone/objects/mission/MissionObjectiveImplementation.cpp:59` |
| `Core3.MissionManager.IncludeFactionPets` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:354` |
| `Core3.MissionManager.ListRequestCooldown` | integer | Active | `MMOCoreORB/src/server/zone/managers/mission/MissionManagerImplementation.cpp:200` |
| `Core3.MissionManager.MaxBountiesPerJedi` | integer | Active | `MMOCoreORB/src/server/zone/managers/mission/MissionManagerImplementation.cpp:2096` |
| `Core3.MissionManager.PlayerBountyCooldown` | boolean | Optional | `MMOCoreORB/src/server/zone/managers/mission/MissionManagerImplementation.cpp:2068` |
| `Core3.MissionManager.PlayerBountyCooldownTime` | integer | Active | `MMOCoreORB/src/server/zone/managers/mission/MissionManagerImplementation.cpp:2160` |
| `Core3.MissionManager.PrivateStructureJediMissions` | boolean | Active | `MMOCoreORB/src/server/zone/managers/mission/MissionManagerImplementation.cpp:2139` |
| `Core3.NameManager.FilterTable` | string | Active | `MMOCoreORB/src/server/zone/managers/name/NameManager.cpp:192` |
| `Core3.NavMeshManager.LogLevel` | log-level | Active | `MMOCoreORB/src/server/zone/managers/collision/NavMeshManager.cpp:22` |
| `Core3.ORB` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:322` |
| `Core3.ORBPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:326` |
| `Core3.OnlineLogSeconds` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:606` |
| `Core3.OnlineLogSize` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:615` |
| `Core3.PathfinderLogJSON` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:554` |
| `Core3.PingAllowedConnections` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:466` |
| `Core3.PingPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:446` |
| `Core3.PlanetManager.ShuttleportAwayTime` | integer | Optional | `MMOCoreORB/src/server/zone/managers/planet/PlanetManagerImplementation.cpp:231` |
| `Core3.PlanetManager.ShuttleportLandedTime` | integer | Optional | `MMOCoreORB/src/server/zone/managers/planet/PlanetManagerImplementation.cpp:232` |
| `Core3.PlanetManager.ShuttleportLandingTime` | integer | Optional | `MMOCoreORB/src/server/zone/managers/planet/PlanetManagerImplementation.cpp:233` |
| `Core3.PlanetManager.StarportAwayTime` | integer | Optional | `MMOCoreORB/src/server/zone/managers/planet/PlanetManagerImplementation.cpp:234` |
| `Core3.PlanetManager.StarportLandedTime` | integer | Optional | `MMOCoreORB/src/server/zone/managers/planet/PlanetManagerImplementation.cpp:235` |
| `Core3.PlanetManager.StarportLandingTime` | integer | Optional | `MMOCoreORB/src/server/zone/managers/planet/PlanetManagerImplementation.cpp:236` |
| `Core3.PlayerCreationManager.EnableTutorial` | boolean | Active | `MMOCoreORB/src/server/zone/managers/player/creation/PlayerCreationManager.cpp:379` |
| `Core3.PlayerCreationManager.MaxCharactersPerGalaxy` | integer | Active | `MMOCoreORB/src/server/zone/managers/player/creation/PlayerCreationManager.cpp:321` |
| `Core3.PlayerLogLevel` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:578` |
| `Core3.PlayerManager.AccountVictimList` | boolean | Active | `MMOCoreORB/src/server/zone/managers/player/PlayerManagerImplementation.cpp:6906` |
| `Core3.PlayerManager.AdvancedWaypoints` | boolean | Active | `MMOCoreORB/src/server/zone/objects/creature/commands/WaypointCommand.h:18` |
| `Core3.PlayerManager.DisableGroupVisibility` | boolean | Active | `MMOCoreORB/src/server/zone/managers/visibility/VisibilityManager.cpp:34` |
| `Core3.PlayerManager.GalaxyWideGrouping` | boolean | Active | `MMOCoreORB/src/server/zone/managers/group/GroupManager.cpp:45` |
| `Core3.PlayerManager.ValidClientVersion` | string | Active | `MMOCoreORB/src/server/zone/packets/zone/ClientIdMessageCallback.h:98` |
| `Core3.PlayerManager.WipeFillingOnClone` | boolean | Active | `MMOCoreORB/src/server/zone/managers/player/PlayerManagerImplementation.cpp:1880` |
| `Core3.PlayerObject.AlwaysSafeLogout` | boolean | Active | `MMOCoreORB/src/server/zone/objects/player/PlayerObjectImplementation.cpp:2337` |
| `Core3.PlayerObject.LinkDeadDelay` | integer | Active | `MMOCoreORB/src/server/zone/objects/player/PlayerObjectImplementation.cpp:2556` |
| `Core3.ProgressMonitors` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:340` |
| `Core3.PurgeDeletedCharacters` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:502` |
| `Core3.PvpMode` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:310` |
| `Core3.RESTServer.APIToken` | string | Active | `MMOCoreORB/src/server/web/RESTServer.cpp:350` |
| `Core3.RESTServer.LogLevel` | integer | Active | `MMOCoreORB/src/server/web/RESTServer.cpp:330` |
| `Core3.RESTServer.RotateLogSizeMB` | integer | Optional | `MMOCoreORB/src/server/web/RESTServer.cpp:38` |
| `Core3.RESTServer.SSLCertFile` | string | Active | `MMOCoreORB/src/server/web/RESTServer.cpp:374` |
| `Core3.RESTServer.SSLKeyFile` | string | Active | `MMOCoreORB/src/server/web/RESTServer.cpp:367` |
| `Core3.RESTServer.WorkerThreads` | integer | Active | `MMOCoreORB/src/server/web/RESTServer.cpp:331` |
| `Core3.RESTServer.exportDir` | string | Active | `MMOCoreORB/src/server/web/APIProxyObjectManager.cpp:328` |
| `Core3.RESTServerPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:562` |
| `Core3.Regions.DisableSpaceSpawns` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:781` |
| `Core3.Regions.DisableWorldSpawns` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:768` |
| `Core3.Regions.minimumLairSpawnInterval` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:742` |
| `Core3.Regions.minimumSpaceSpawnInterval` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:755` |
| `Core3.Regions.spaceSpawnCheckRange` | number | Active | `MMOCoreORB/src/conf/ConfigManager.h:807` |
| `Core3.Regions.spawnCheckRange` | number | Active | `MMOCoreORB/src/conf/ConfigManager.h:794` |
| `Core3.RegistrationMessage` | string | Active | `MMOCoreORB/src/server/login/account/AccountManager.cpp:234` |
| `Core3.RotateLogAtStart` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:526` |
| `Core3.RotateLogSizeMB` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:522` |
| `Core3.SameAccountTipsAreFree` | boolean | Active | `MMOCoreORB/src/server/zone/objects/creature/commands/TipCommand.h:104` |
| `Core3.SceneObject.exportDir` | string | Active | `MMOCoreORB/src/server/zone/objects/scene/SceneObjectImplementation.cpp:2547` |
| `Core3.SessionStatsSeconds` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:591` |
| `Core3.ShipAiAgent.LogLevel` | integer | Optional | `MMOCoreORB/src/server/zone/objects/ship/ai/ShipAiAgentImplementation.cpp:356` |
| `Core3.ShuttleZoneComponent.BootDelay` | integer | Active | `MMOCoreORB/src/server/zone/objects/building/components/ShuttleZoneComponent.cpp:48` |
| `Core3.SpaceZone.ThreadsDefault` | integer | Active | `MMOCoreORB/src/server/zone/SpaceZoneImplementation.cpp:28` |
| `Core3.SpaceZonesEnabled` | sorted string array | Active | `MMOCoreORB/src/conf/ConfigManager.h:498` |
| `Core3.StatusAllowedConnections` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:462` |
| `Core3.StatusInterval` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:470` |
| `Core3.StatusPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:442` |
| `Core3.StructureMaintenanceTask.AllowBankPayments` | boolean | Active | `MMOCoreORB/src/server/zone/managers/structure/StructureManager.cpp:1376` |
| `Core3.StructureManager.EnhancedFurnitureRotate` | boolean | Active | `MMOCoreORB/src/server/zone/objects/creature/commands/RotateFurnitureCommand.h:30` |
| `Core3.StructureObject.MaintenanceBootDelay` | integer | Active | `MMOCoreORB/src/server/zone/objects/structure/StructureObjectImplementation.cpp:428` |
| `Core3.TangibleObject.ForceNoTradeADKMessage` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:654` |
| `Core3.TangibleObject.ForceNoTradeMessage` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:641` |
| `Core3.TangibleObject.NoTradeMessage` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:628` |
| `Core3.TermsOfService` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:534` |
| `Core3.TermsOfServiceVersion` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:538` |
| `Core3.TransactionLog.AsyncExport` | boolean | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:917` |
| `Core3.TransactionLog.CheckPlayerDebug` | boolean | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:925` |
| `Core3.TransactionLog.Enabled` | boolean | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:915` |
| `Core3.TransactionLog.LogLevel` | log-level | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:411` |
| `Core3.TransactionLog.PruneCraftedComponents` | boolean | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:923` |
| `Core3.TransactionLog.PruneCreatureObjects` | boolean | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:921` |
| `Core3.TransactionLog.RotateLogSizeMB` | integer | Optional | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:410` |
| `Core3.TransactionLog.Verbose` | boolean | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:919` |
| `Core3.TransactionLog.WorkerThreads` | integer | Active | `MMOCoreORB/src/server/zone/objects/transaction/TransactionLog.cpp:421` |
| `Core3.TreFiles` | string array | Active | `MMOCoreORB/src/conf/ConfigManager.h:394` |
| `Core3.TreManager.ReloadStrings` | boolean | Active | `MMOCoreORB/src/server/zone/managers/stringid/StringIdManager.cpp:90` |
| `Core3.TrePath` | string | Active | `MMOCoreORB/src/conf/ConfigManager.h:434` |
| `Core3.Tweaks.StructureObject.DestroyOrphans` | boolean | Active | `MMOCoreORB/src/server/zone/objects/structure/StructureObjectImplementation.cpp:231` |
| `Core3.UnloadContainers` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:280` |
| `Core3.UseMetrics` | boolean | Active | `MMOCoreORB/src/conf/ConfigManager.h:294` |
| `Core3.Zone.ThreadsDefault` | integer | Active | `MMOCoreORB/src/server/zone/GroundZoneImplementation.cpp:36` |
| `Core3.ZoneAllowedConnections` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:482` |
| `Core3.ZoneGalaxyID` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:486` |
| `Core3.ZonePortsBalancer` | integer | Active | `MMOCoreORB/src/server/login/objects/Galaxy.h:125` |
| `Core3.ZoneServer.ClientLogLevel` | integer | Active | `MMOCoreORB/src/server/zone/ZoneClientSessionImplementation.cpp:49` |
| `Core3.ZoneServerPort` | integer | Active | `MMOCoreORB/src/conf/ConfigManager.h:490` |
| `Core3.ZonesEnabled` | sorted string array | Active | `MMOCoreORB/src/conf/ConfigManager.h:494` |
