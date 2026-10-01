# Project Updates

## 2026-09-30

### Committed indoor and outdoor city trainer placement

- City trainers, SpyNet informants, and faction recruiters can now be placed outdoors within the mayor's city or indoors in its civic buildings and player cantinas, hospitals, and theaters. Mayors need building administrator access for player buildings; game admins bypass mayor and building-access requirements. Indoor NPCs spawn in the player's cell. The city charges the same 1,000-credit recruitment cost and ongoing upkeep in both locations, and mayors or game admins can remove them. City-radius cleanup now uses world coordinates so an indoor trainer is not mistaken for an out-of-bounds NPC during an update. Source and whitespace review passed, and the user verified the change. No necessary verification remains. The assistant did not build or run Core3.

### Committed city recruitable NPCs

- Extended `/recruitSkillTrainer` with one SpyNet informant choice plus Rebel and Imperial recruiters. The existing city trainer choices remain. The informant works with all Bounty Hunter investigation levels. These NPCs use city trainer capacity, treasury cost, upkeep, and persistence. Mayors can remove recruited NPCs with the Remove radial; the option is hidden for unrelated NPCs that share an appearance. Source, template, and whitespace review passed, and the user verified the change. No necessary verification remains. The assistant did not build or run Core3.

### Committed SpyNet informant access

- SpyNet informants now provide bounty investigation information regardless of the informant's old level and the player's investigation level. Bounty Hunter skill and an active bounty mission are still required. Mission progression uses the mission's level so its waypoint behavior remains correct. Source and whitespace review passed, and the user verified the change. No necessary verification remains. The assistant did not build or run Core3.

### Committed structure item search

- Added **Find Item by Name** to Structure Management in buildings with item storage. An administrator enters a keyword, selects a matching stored item, and moves it to their feet. The search includes items inside containers and limits the result list to 100 entries. Access and item location are checked again when the result is selected. The user's first build found pointer-type errors, which were corrected; the user subsequently verified the change. Source and whitespace review passed, and no necessary verification remains. The assistant did not build or run Core3.

## 2026-09-29

### Committed account structure list in `/find`

- Added `/find lots` to list structures owned by any character on the account, with assigned lots, maintenance balance, power on installations that consume it, and city treasury where applicable. Generators do not show a power balance. Structures within city limits include the city after their name, such as `City Hall / Chicago`. It also shows total account lots used and available. Source and whitespace review passed; the user verified the change. No necessary verification remains. The assistant did not build or run Core3.

### Committed city militia zoning rights

- City militia members now have zoning rights automatically for as long as they serve. Militia members can already use `/grantZoningRights`; the command now explains that temporary grants cannot be toggled for another militia member. Source review and whitespace checks passed, and the user verified the change in game. No necessary verification remains. The assistant did not build or run Core3.

### Committed structure planet placement option

- Added `Core3.StructureManager.AllowPlacementOnAllPlanets = true` to both configuration files. When enabled, structure deeds ignore their template planet lists, and the deed’s “Can Be Built On” detail shows **All Planets**. Turning it off restores the template list and original placement restriction; terrain, zoning, faction, and other placement rules remain. Source and whitespace review passed, and the user verified the change and requested the commit. No necessary verification remains. The assistant did not build or run Core3.

### Committed city population downgrade override

- Added an admin-only **City Hacks → Ignore Citizen Requirements** toggle, saved on each city and off by default. When on, scheduled city updates do not downgrade the city because its citizen count is below the current rank requirement. It remains enabled across restarts and mayor changes until an admin turns it off. Elections, maintenance, tax processing, population-based advancement, and the admin force-rank action remain available. Source and whitespace review passed; the user verified all changes and requested the commit. No necessary verification remains. The assistant did not build or run Core3.

### Removal of Codex test scripts and notes

- Removed all 26 Codex-created standalone test scripts from `MMOCoreORB/src/tests/standalone`, plus two Codex-created audit/dependency notes under `MMOCoreORB/bin/docs` that the user removed. Existing project tests and test-named game content remain. Earlier update entries describing results from the scripts remain historical records; the files are no longer present in the working tree. Verification was skipped at the user's explicit request before committing.

### Committed quick city treasury deposit

- The mayor now has a Quick Options treasury deposit at the city management terminal. Its per-city amount defaults to 100,000 credits, uses a compact radial label such as `100k Treasury Deposit`, and can be changed under City Treasury. Setting it to zero hides the shortcut and Quick Options menu. An existing city displayed an invalid 901.9M amount because old-city loading skipped the initialization path for the new field; a field-level default and load-time range check now protect older cities while preserving valid saved settings, including zero. The user confirmed all changes are verified and requested the commit; no necessary verification remains. The assistant did not build or run Core3.

### Committed structure quick options

- Added an account-owner Quick Options radial for per-structure quick maintenance, quick power on powered installations, and withdraw-all resources on harvesters and generators. Structure Management lets owning-account characters set separate saved maintenance and power amounts for each structure; both default to 10,000. Setting one to zero hides that shortcut, and Quick Options disappears when it has no actions. Withdraw All Resources remains available on harvesters even when both amounts are zero. Quick menu labels shorten amounts, such as `10k Maintenance` or `100k Power`. Existing admins outside the owning account do not receive these options.
- Moved Operate Machinery to the first main radial position on harvesters and generators, followed by Quick Options and Structure Management. Houses show Quick Options before Structure Management. Source and whitespace review passed; the user verified all changes working in game and requested the commit. No necessary verification remains. The assistant did not build or run Core3.

### Civic structure status cleanup

- Structure Status no longer adds an empty privileged debug row. Civic structures without a maintenance warning now show no blank line, while actual warnings still appear. Source and whitespace review passed, and the user verified the fix in game.

### Committed additional structure storage lots

- Added **Structure Management → Add Storage Lots / Remove Storage Lots** for buildings that already consume lots. Only characters on the owning account receive these options; ordinary structure admins do not. Each option appears only when a valid adjustment is available.
- The add/remove window uses the client's existing transfer slider. Added lots use the shared account allowance and increase storage by the configured `ItemsPerLot`; each building can add at most twice its original lot cost. A two-lot house can therefore have up to four added lots, six total. Players cannot remove a building's base lots or reduce capacity below its current contents. The structure report shows base, added, and total lots alongside storage usage.
- Added lots persist across restarts and ownership transfers. Player-initiated destruction and redeeding cancel while any added lots remain; the player must remove them first. Server cleanup still frees all lots if it destroys a structure. A newly placed deed starts at its normal base cost. Zero-lot buildings retain their configured capacity and have no lot-adjustment menus.
- All 1,280 targeted standalone checks passed, including the slider, twice-base limit, and destruction/redeed block; source and whitespace review passed. The user confirmed all changes are verified and requested this commit. No necessary verification remains. No TRE update is needed; the assistant did not build or run Core3.

### Committed project guidance update

- The user replaced root `AGENTS.md` with concise workspace, source, commit, testing, and history guidance, and now requires a dependency summary and confirmation before MTGServer ports. A later user edit also prohibited automatic test-file creation without the stated explicit request. The standalone tests in this change were written before that new rule appeared. The user's wording was preserved and trailing whitespace was cleaned.

### Committed structure capacity configuration

- Added `Core3.StructureManager.ItemsPerLot = 200`, `NoLotItemCount = 1000`, and `LotsPerCharacter = 10` to both configuration files, preserving the current defaults. Building storage and the structure report use the configured limits; the shared account lot pool uses maximum character slots times `LotsPerCharacter`, plus its admin bonus.
- Zero/negative settings provide zero base capacity, and large calculations avoid integer overflow. Existing items, structures, admin bonuses, and historical lot-bonus migration are preserved when settings change.
- Verification passed: 173 lot-capacity/bonus checks and 68 storage/configuration checks, including Lua validation of both files and strict-C++11 overflow checks. Source/caller and whitespace review passed. The user confirmed all changes are verified and requested the commit. This overall runtime confirmation supersedes the pending rebuild/restart and in-game checklist; no necessary verification remains. No TRE update is needed, and the assistant has not built or run Core3.

### Committed shared account lots and structure permissions

- Replaced separate character lot allowances with a shared account pool in the current galaxy: `Core3.PlayerCreationManager.MaxCharactersPerGalaxy * 10`, plus an account-wide admin bonus. Updated the explanatory comment in both configuration files. `/adjustLotCount` now adjusts the whole account; existing character bonuses migrate once.
- Offline owners count toward the pool. Construction reserves lots and returns them on cancellation/failure; placement, displays, transfers, redeeding, and destruction use the shared balance. Same-account transfers consume no additional lots, even when the pool is full. Corrected the ledger's reported build error for C++11 compatibility.
- Characters on the owner's account receive owner-level structure management rights, including private-house access, administration, maintenance, installation controls, transferring, redeeding, and destruction. Residence remains with the named owner, as requested; existing no-trade, faction, and civic restrictions remain.
- Added **Structure Management → Take Ownership** for an alt to claim an eligible non-residence house or installation while the named owner is offline. Shared lot usage stays unchanged, and the alt can then declare the house as its residence. Special civic/faction/guild/camp ownership remains separate.
- Destruction confirmations recheck ownership and their original session; pending destruction prevents competing redeeds/transfers. Fixed the reported confirmation freeze by accepting the input window's normal two-field response, clearing invalid-code attempts, and removing stale destruction confirmations on login. Redeeding returns the deed to the acting character while cleanup uses the actual owner's records.
- All 967 standalone checks and source/whitespace review passed. On September 29, the user confirmed everything is verified and requested the commit, including the final destruction fix. This overall runtime confirmation supersedes the pending verification checklist; no necessary checks remain. No TRE update is needed, and the assistant has not built or run Core3.

## 2026-09-28

### Committed structure storage limits and reporting

- Building storage now allows 200 items per lot with no separate per-building cap. All zero-lot buildings, including civic structures, allow 1,000 items, as clarified by the user.
- Floor placement and transfers into containers inside buildings use the same updated limit. Existing buildings adopt it after a Core3 rebuild/restart; no TRE update or database migration is needed.
- The building structure report now shows `Storage Used: item count / max storage` on one line, using the same limit and counting methods as storage enforcement. Refresh recalculates both values.
- Source/caller, report-refresh, numeric-range, and whitespace review passed. The user verified that lot-based storage and the structure report are working and requested the commit. This overall runtime confirmation supersedes the pending checklist; no necessary verification remains. The assistant has not built or run Core3.

### Committed Medium Corellia House Style 2 schematic

- Added the Medium Corellia House (Style 2) draft schematic to Architect Buildings III. Completed its server recipe using the existing medium Corellian house's materials and 8,000 XP, registered it for crafting, and staged its skill-group assignment in `SWGFR_update_01/datatables/crafting/schematic_group.iff`.
- Added the missing client name and description for the style-2 deed, fixing its unresolved skill-window string references. The name is "Deed for: Medium Corellia House (Style 2)"; the server deed uses the same name. Preserved the user's subsequent `deed_detail.stf` edit and verified that all existing description keys/text remain intact. The supplied description says Corellia only; the unchanged house allows Corellia and Talus.
- Diagnosed an unnamed admin-generated deed as a deployment issue: the installed server update TRE lacked both new deed string tables, so `/object createitem` saved only " (System Generated)". The user acknowledged the missing archive deployment and subsequently confirmed the new deed and draft schematic work perfectly. No additional source or asset change was needed.
- Lua, recipe/deed/house dependency, binary-table/string preservation, and whitespace checks passed. The user's final overall runtime confirmation supersedes the pending deployment and in-game checklist; no necessary verification remains for this commit. Existing Architects receive the schematic when their character loads after restart. No Core3 compilation is needed; the assistant has not built or run Core3.

### Committed SWGFR staff tags

- Changed all 12 active elevated-player tag definitions from `SWGEmu-` to `SWGFR-`, retaining their role suffixes, such as `SWGFR-Admin`, `SWGFR-Dev`, and `SWGFR-CSR`. Character, chat, and ship displays use these shared definitions.
- Static verification passed: the complete staff Lua include chain loads all 13 roles, with 12 SWGFR staff tags and an empty ordinary-player tag. Byte comparisons confirm only the requested prefixes changed; source and whitespace review passed.
- The user confirmed the staff tags are working and requested the commit after receiving the restart/login and character/chat display checklist. This overall runtime confirmation supersedes the pending verification; no necessary checks remain. No Core3 rebuild or TRE update is required. The assistant has not built or run Core3.

### Committed faction rank limits from TRE data

- Recruiter promotions and the admin `/setFaction` rank limit now follow the loaded `datatables/faction/rank.iff` instead of stopping at rank 15, Colonel. The active TRE table has 22 ranks, ending at rank 21, Surface Marshal, making six additional ranks attainable with their existing faction-point costs.
- Recruiter confirmation and acceptance recheck the limit and reject invalid next-rank costs, preventing an outdated promotion conversation from assigning a rank beyond the table or charging points for it. Existing faction-point minimums and rank benefits remain unchanged.
- Static verification passed: all 143 standalone rank-limit/admin/recruiter checks, recruiter Lua syntax, active-TRE rank/name/cost validation, and source/whitespace review. The test reproduces the original rank-15 restriction against the pre-fix commit.
- The user confirmed everything is working and requested the commit after receiving the rebuild/restart, recruiter promotion, final-rank, point-deduction, relog, and `/setFaction` checklist. This overall runtime confirmation supersedes the pending verification; no necessary checks remain. The implementation and 143 passing standalone checks remain applicable. No TRE update is required, and the assistant has not built or run Core3.

## 2026-09-27

### Committed character tutorial room and item-box fix

- Corrected two misspelled room-name checks that made the tutorial ignore the player's current room and completed rooms. This restores the introductory sequence and the officer-conversation step that grants access to the starting-item box.
- Static verification passed: all 34 standalone tutorial checks, syntax checks for all 12 tutorial screenplay files, source/permission-path review, and whitespace checks. The standalone test reproduces the original room-detection failure against the pre-fix commit.
- The user confirmed the tutorial is verified and requested the commit after receiving the introductory-prompt, officer/box, and inventory-progression checklist. This overall runtime confirmation supersedes the pending checks; no necessary verification remains. This Lua-only fix requires no Core3 compilation or client TRE update. The assistant has not built or run Core3.

### Committed helper droid configuration and login lifecycle

- Added `Core3.HelperDroid.Enabled` and `Core3.HelperDroid.AutoCallOnZone` together in both configuration files, with shared defaults enabled and the user's local settings preserved. With zone auto-calls off, the initial planet arrival and six novice-profession triggers still call the helper; later login/travel/zoning does not recall it. Existing age limits apply to those automatic summons.
- When disabled, login now removes the helper and its datapad device, clears its ship assignments, and preserves quest progress. When enabled, a missing helper is restored on login as a stored device, including for older characters, unless that player manually deleted it. Confirmed manual deletion is remembered across logins and prevents automatic replacement. The user chose to give a stored helper to older characters whose previous deletion history is unknown.
- The user verified the earlier behavior: first-planet spawning, no recall after travel or logout/login with auto-calls off, calling after a new novice box, and no calls when disabled. The user subsequently confirmed everything is verified, including the final login deletion/restoration and manual opt-out changes, and requested this commit. This overall confirmation supersedes the pending runtime checklist; no necessary verification remains. All 218 standalone lifecycle, cleanup, ship, and Lua checks pass, along with configuration syntax and source/whitespace review; the assistant has not built or run Core3.

### Committed Empty Mail Target command-browser assets

- Added the missing English `cmd_n:emptymailtarget` name, **Empty Mail Target**, and `cmd_d:emptymailtarget` description explaining mailbox deletion for a selected player or specified first name, with `/emptyMail` for the admin's own mailbox.
- Assigned the existing mail-envelope icon to the command in both ground and space UI styles. All three client files are staged only in `SWGFR_update_01`; no new texture or server behavior change is needed.
- Binary string-table and UI dependency checks passed, including independent verification that every existing entry is preserved. The user confirmed the changes are working and requested this commit. This overall client verification supersedes the pending deployment/display checklist; no necessary verification remains. The assistant did not rebuild or install a TRE or run Core3.

### Committed admin skill revocation selection and confirmation

- `/revokeSkill` now opens an alphabetical skill list for the targeted player, or for the admin issuing the command when no target is selected. Invalid explicit targets are rejected. `/revokeSkill all` previews all revocable skills for either target choice.
- Selecting a skill previews its learned dependents and the returned skill points before confirmation. Both lists are alphabetical. The window identifies and retains the original player, and changed skill plans require another confirmation.
- Admin access is checked when the command starts and again during selection/confirmation. Pilot revocation remains available to admins; innate, language, staff, and protected progression skills remain. The shared eligibility check explicitly protects Force ranking skills against unlisted rank-removal effects.
- All 39 new revocation checks, 17 updated eligibility/planning checks, and 28 surrender confirmation checks pass. Earlier results for the unchanged dependency planner and Jedi rules remain applicable, for 127 related standalone checks in total. Source/caller/locking review and whitespace checks passed. The user confirmed `/revokeSkill` is working appropriately and requested this commit. This overall runtime confirmation supersedes the pending verification checklist; no necessary verification remains. The assistant has not built or run Core3.

### Committed skill surrender selection and confirmation

- `/surrenderSkill` now lists learned skills that can be surrendered. Both the selection and confirmation lists are alphabetical by skill display name, ignoring capitalization. Selecting a skill previews that skill and every learned skill that requires it, including dependent professions. Selecting Novice Entertainer therefore includes its learned Entertainer, Dancer, and Musician dependents.
- The confirmation lists all planned removals and the skill points to recover. Cancel keeps every skill. `/surrenderSkill all` previews all currently surrenderable skills through the same confirmation flow; innate, language, staff, pilot, and protected progression skills remain.
- Removal follows prerequisite order and uses the existing surrender behavior for refunds, abilities, modifiers, and schematics. Changed skill lists require another confirmation, and Jedi progression requirements are checked against the complete plan before surrender starts. Zero-point profession boxes are included.
- All 84 standalone dependency, eligibility, display ordering, confirmation/cancellation, and Jedi progression checks pass. Source/caller and whitespace review passed. After the alphabetical-list refinement, the user confirmed everything is working correctly and requested this commit. This overall runtime confirmation supersedes the pending verification checklist; no necessary verification remains. The assistant has not built or run Core3.

### Committed shutdown session disconnect and login logging fixes

- Fixed shutdown walking the online-account map while each disconnect changes that same map, which could skip other connected players. Shutdown now captures all player sessions first and releases the map lock before disconnecting them, including multiple accounts or characters sharing one IP.
- The initial disconnect message now counts sessions rather than accounts. The existing wait reports a warning if players remain connected instead of always reporting success. Logout behavior, the wait duration, and final save/cleanup ordering are preserved.
- All 14 standalone regression checks passed; the previous code failed nine. Source/caller, lock-order, and whitespace review passed. The reviewed user-run server logged four distinct players across two accounts on one IP, then processed all four disconnects at `14:51:56` without exhausting the wait. The save and zone cleanup completed without shutdown warnings/errors. The user confirmed all four clients disconnected appropriately and subsequently verified the final changes work as intended before requesting this commit.
- Investigated the console showing only three logged-in players during that run: the fourth login was recorded correctly, but arrived 4.175 seconds after the third, inside the existing five-second console-summary throttle. During shutdown, a separate three-player snapshot was recorded after the first player was marked offline. Clarified the message to say `Online player snapshot: N players currently online` so it describes current status rather than appearing to count completed logins or disconnects.
- Completed logins now force an immediate console snapshot, including logins less than five seconds apart or with an unchanged total. Normal status updates retain the throttle, and session-change file logging still follows its existing setting.
- Normal shutdown now forces the full online snapshot before the disconnect-start messages and suppresses intermediate shutdown snapshots on the console. File records and statistics continue updating during each logout. All 14 existing disconnect regression checks still pass; source/order and whitespace review passed. The user's final verification supersedes the earlier pending runtime checklist. No necessary verification remains for this commit.

### Committed shutdown cleanup improvement

- Corrected ground and space cleanup to remove the departing object from nearby-object lists. The previous calls targeted the zone instead, leaving the object's list populated and causing repeated scans.
- Limited cleanup through a parent's nearby-object list to one pass while preserving the parent's relationships. Objects with their own lists retain the existing cleanup retries. The full save, player disconnection, shutdown ordering, and remaining object cleanup are unchanged.
- All 20 standalone cleanup regression checks passed; the previous code failed six. Representative affected cases now require one list scan instead of 100. Source/locking review and whitespace checks passed. The user subsequently rebuilt, started, and shut down Core3.
- Verified the latest normal shutdown at `08:12:15`: logged shutdown time fell from 59.329 to 26.587 seconds (55.2% shorter), all-ground cleanup from 48.713 to 14.205 seconds, and Tatooine from 40.029 to 12.840 seconds with the same 10,639 objects. Both runs cleared the same 12 ground and 10 space zones. The full save completed before cleanup; the latest shutdown logged no warnings or errors. The user subsequently confirmed the post-shutdown saved-data and ground/space interaction checks passed. No necessary verification remains for this commit.

### Committed vehicle recovery fix

- Fixed a database-load race that could put a vehicle back into the world after login had already stored it and cleared its owner link. Deferred insertion now checks that the object still belongs to the saved zone and has not already been inserted.
- All 11 isolated task regression cases passed; the same harness reproduced six failures against the pre-fix committed task. Source/locking review and whitespace checks passed. The user subsequently tested the fix several times in game and confirmed it works as intended.
- Existing affected vehicles with intact datapad references can use the normal login storage and subsequent call path to recover. User-confirmed runtime testing supersedes the pending verification for the reported vehicle issue. No necessary verification remains for this commit.

### Committed configuration cleanup

- Audited main configuration consumers in `src` and `bin`, then organized both Lua config files into matching sections. Each now documents 150 active settings, 15 optional overrides, and five dynamic key families. Added missing source-backed settings, removed seven unused entries, and renamed `DeleteCharacters` to `PurgeDeletedCharacters`.
- The user restored the commented TEST-zone options in both configurations: 17 ground zones and six space zones. They remain disabled; the enabled-world lists are unchanged. Lua syntax/evaluation and whitespace checks passed after the additions.
- Corrected the orphan-removal spelling, victim-list namespace, and ship AI logging reader. Legacy aliases remain supported. Preserved existing effective settings and private local values; the local file stays ignored. Standalone Lua/value/coverage checks passed. The updated executable and September 27 startup/login logs verify the current changes: startup completed with no errors and only the seven known asset warnings, followed by a player entering a world. The user confirmed everything looks good. Optional switch/debug behavior remains covered by static checks rather than dedicated runtime tests; no necessary verification remains for this commit.

### Committed startup and asset changes

- Reviewed 11 user-added assets in `SWGFR_update_01`: a pilot-chair template, six empty ship-table placeholders, and four populated ship tables. The chair references an existing pilot-station slot descriptor; the four populated tables still require 45 missing client attachments and matching server definitions. Preserved all additions and documented their limitations.
- Verified the latest startup at `00:24:11` completes in about 35 seconds, with the asteroid-table warnings and `engine3.lua` error gone. The user reports that all looks good following the requested rebuild/startup. All 26 staged assets were already verified byte-for-byte in the installed TRE. Seven warning lines remain for the documented missing client assets; the user also confirmed resource surveying/sampling, correct harvested containers, ship component installation/appearance/targeting/collision, and pilot-chair use passed with the update TRE on the client. No necessary verification remains for this commit.
- Added the remaining working-directory `bin/engine3.lua` entry point without settings, preserving engine defaults. Standalone Lua syntax/execution checks and the latest user startup passed.
- Corrected ship loading to skip component tables for chassis without component slots. Static checks confirm this removes only the two mining-asteroid table probes while retaining all 311 other reads; the latest startup confirms both warnings are gone. The three ship CDFs, Corvette portal layout, and Corellia particle effect remain genuine missing assets without verified replacements.

## 2026-09-26

### Committed startup and asset changes

- Investigated the latest successful Core3 startup separately from earlier failed attempts. Corrected optional configuration loading, an obsolete city setting, resource/station template types, and misleading particle-appearance diagnostics.
- Restored the missing vehicle-component base, two appearance redirects, and 12 verified ship component tables from existing authorized MTG archives, stored only in `SWGFR_update_01`. Consolidated duplicate ship-data reads and corrected appearance-slot mapping for sparse ship tables. Static verification passed; the September 27 entry records subsequent startup verification. The September 27 entry also records passing user gameplay checks.
- Recorded the asset-staging preference and removed all 15 duplicate loose assets from `bin`. Added `SWGFR_update_01.tre` first in both Lua configurations and aligned ConfigManager's latest-TRE default. The original 15 assets were subsequently verified in the user-installed archive; `config-local.lua` remains ignored.

### Previously committed changes

- Clarified project guidance: MTGServer is an authorized source for relevant fixes and content; importing from unauthorized projects or branches remains prohibited. Verification records must distinguish static checks from user-confirmed Core3 builds and runtime testing. Commit requests now require reviewing verification and resolving outstanding checks unless the user explicitly requests a commit without verification.
- Created `MMOCoreORB/bin/conf/config-local.lua` as an exact copy of `config.lua` for local configuration. Verified that the existing Git ignore rules exclude it and that it is not tracked.
- Added ignore rules for the local `swgemu-SWGFR.sql` and `mantis-SWGFR.sql` files. Both were already untracked and remain present locally, unchanged.
- Removed the generated `MMOCoreORB/bin/scripts/managers/resource_manager_spawns.lua` from Git tracking and deleted the old local copy. The user confirmed full Core3 startup; verified that the file regenerated with resource entries and remains ignored and untracked.
