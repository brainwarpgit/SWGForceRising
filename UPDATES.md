# Project Updates

## 2026-10-07

### Committed group creature-credit bonus

- Creature credits looted while grouped now increase by 50% of the original total for each additional player member: two players receive 1.5×, four receive 2.5×. Pets and droids do not count. The bonus applies after the existing Luck credit adjustment and before nearby group members split the payout; it also covers direct creature looting by a grouped player. The existing payout message says when the group bonus is included, without sending a separate message. The update TRE adds these message variants. Missions, slicing rewards, transfers, and other credit sources are unchanged. The user verified the final behavior in game.

### Committed locked-loot slicing credit rewards

- Successfully slicing a locked loot container or briefcase now pays cash credits in addition to the existing loot roll. Normal rewards roll 250–500, Exceptional 750–1,250, and Legendary 2,500–3,000. Base chances are 15% Exceptional and 5% Legendary; each Luck or Force Luck point adds 0.2 and 0.1 percentage points respectively. Each failed attempt before success reduces the rolled amount by 25%. The final payout and tier appear in a system message. The user verified the reward in game.

### Committed locked-container slicing and briefcase display updates

- `Core3.SlicingContainerRetries` now controls extra attempts for locked loot containers and briefcases. Its default is `0`, retaining the original one-attempt behavior; setting it to `2` allows three total attempts, with the remaining count shown on examine and preserved across restarts. Exhausted attempts show a broken lock and rename the item **Broken Locked Container** or **Broken Locked Briefcase**.
- Looted briefcases retain their slicing behavior and attempt state after restart. Locked and unlocked briefcases use localized names without the redundant “Variation Of” line. The update TRE adds the attempt label and briefcase/container names. The appearance loader no longer reports `SPRT` UI sprites as unknown world appearances.
- The user verified the final behavior in game. The tracked configuration defaults to `0`; the ignored local configuration keeps the user's `2`-retry testing override.

## 2026-10-05

### Committed timed mission-terminal slicing bonus

- A sliced mission terminal now offers a timed payout bonus across mission refreshes. `Core3.MissionManager.TerminalSliceBonusDurationSeconds` in both configuration files defaults to 60 seconds; `0` disables the bonus. Slicing + Luck + Force Luck is capped at 150 and scales payouts from the unchanged base at zero to at most 2× at 150. The slicer sees the bonus and its duration when successful and receives an expiry message when the bonus ends, including when solo. Nearby group members within 64 meters can use the same bonus and receive a system message, a waypoint removed when the configured window ends, and an expiry message. Only one active slice session can use a mission terminal at a time; another slicer is told when their group member is already slicing it. After a successful slice, the slicer and that terminal must wait through the bonus window and then a two-minute cooldown before slicing again. Failed slices retain the existing personal two-minute cooldown. The user verified the payout, cooldown, and group behavior in game.

### Committed weapon and armor slice details

- Examining a newly sliced weapon or armor piece now shows the slicer, slice type, and percentage under a shared Slice Attributes heading. The percentage label is shortened to “Slice %.” These details are stored in dedicated weapon and armor fields; containers and briefcases retain their existing examine layout. The user verified the presentation in game.

### Committed Master Smuggler slicing choice

- Master Smugglers can choose Damage or Speed for successful weapon slices and Effectiveness or Encumbrance for successful armor slices. Other slicers keep the existing random result. The Master Smuggler skill box shows a display-only Slicing Choice ability in the update TRE. The user verified the behavior in game.

### Committed regrantSkills skill-mod refresh fix

- `/regrantSkills` now reconciles skill-box modifiers newly added to or removed from learned skills and notifies the client when a value changes. The temporary Force Luck test bonus was removed from Master Smuggler, and the user verified that the refreshed value is correct. Successful reconciliation no longer emits a misleading skill-box mismatch warning.

## 2026-10-04

### Committed Slicing skill modifier

- Clothing and armor attachments and looted clothing can now roll Slicing. Smuggler boxes grant +10 Novice, +10/+15/+15/+25 across Slicing I–IV, and +25 Master. Training narrows the weapon and armor slice range; Master Smugglers with more than 100 Slicing gain stronger slices. The update TRE adds the skill name, description, and box bonuses.

### Committed locked briefcase slicing

- Newly looted locked briefcases can be sliced like locked loot crates. Slicing replaces one with an openable “Unlocked Briefcase” holding the same loot roll and keeping the briefcase appearance. The update TRE stages the new container template and its object-template CRC table entry. Quest briefcases keep their existing behavior.

### Committed luck-based credit loot

- Luck and Force Luck now combine to increase credits looted from creatures. A random roll from their total adds effective creature levels to the existing credit roll. In groups, the looter's bonus increases the amount shared among eligible members.

### Committed luck attachments and skill names

- Luck can now roll on looted clothing and armor attachments and on looted clothing. The update TRE source adds separate Luck and Force Luck names and general descriptions; Force Luck keeps a Jedi theme.

### Committed attachment creation command

- Admins can use `/object createattachment clothing luck 25` or `/object createattachment armor luck 23` to create a named, single-mod attachment in their inventory. The command accepts skill-mod values from 1 to 25.

### Committed looted wearable sockets

- Newly looted clothing, armor, and wearable containers can roll 0–4 sockets using the creature-level-weighted loot distribution. `Core3.LootManager.LootedWearableSockets` enables or disables this without changing crafted wearables or existing items. The tracked configuration is disabled; the local configuration is enabled.

### Committed quick-option visibility

- Installation Quick Maintenance and Quick Power appear independently when their own amounts are enabled. Withdraw All Resources appears only when a harvester or generator has retrievable resources in its hopper; Quick Options hides when no shortcuts remain. Building, vendor, and city shortcuts continue to hide when their configured quick amount is zero.

## 2026-10-03

### Committed vendor relisting

- Vendor owners see a Relist All Expired Items radial only when that vendor has expired items, including fixed-price listings whose deadline has passed. It relists all eligible items at their existing prices for the normal vendor listing duration.

### Committed per-vendor Quick Maintenance

- Each vendor now has its own Quick Maintenance amount, defaulting to 10,000 credits. The owner can pay it from Quick Options or change it under Vendor Control; setting it to zero hides the shortcut. The regular vendor payment limit and credit checks apply. The user verified the behavior in game.

### Committed vendor maintenance notices

- Vendors send the owner a low-maintenance email when the balance reaches 300 credits or less, then a disabled email when it reaches zero or below. Each includes the vendor name, planet, current balance, and a waypoint. Notices are sent once per threshold crossing and reset when maintenance is replenished. The user verified the behavior in game.

### Committed vendor maintenance sliders

- Vendor Pay Maintenance and Withdraw Maintenance now use slider windows showing the available amount and selected payment or withdrawal. The existing payment cap and balance checks remain in place. Source and whitespace checks passed, and the user verified the behavior in game.

### Committed vendor skimming

- Master Merchants can set a separate 0–100% sale skim on each vendor. The skim goes into vendor maintenance after city sales tax is deducted; the rest is deposited into the seller's bank account. Vendor sale mail shows tax, skim, updated maintenance, and the bank deposit. A vendor's skim resets to zero when its owner loses Master Merchant. The update TRE stages a display-only Vendor Skimming ability in the Master Merchant skill box. Source and client asset format checks passed, and the user verified the behavior in game.

### Committed weapon insurance

- Eligible weapons can now be insured through the insurance terminal, individually or with Insure All. Insured weapons receive the existing reduced condition decay on death. The default weapon and other existing exclusions remain excluded. The user verified the behavior in game.

## 2026-10-02

### Committed attachment names showing skill mods

- Clothing and armor attachment names now show only each skill-mod name and its signed value, such as `Rifle Accuracy: +12`. Existing attachments update when loaded, and new attachments receive the name when their mods are rolled during loot generation. The user verified the behavior in game.

### Committed ground object visibility range

- Increased the server's ground close-object range from 192 to 512. Space visibility keeps its separate range. The user verified the change in game.

### Committed baby creature highlighting in Area Track

- `/areatrack` results are listed nearest first. Baby creatures in the animal list display in gold while retaining their names and direction/distance details. The user verified the behavior in game.

### Committed crafting and repair effectiveness

- Assembly and experimentation now use the combined effectiveness of the selected crafting tool and station. Experimentation no longer mistakes its failure-rate value for effectiveness. Repair-tool item repairs use the best compatible ready crafting tool in inventory and a nearby matching station; repair-tool quality remains a separate factor. The user verified the change.

### Committed skill refresh command

- Added `/regrantSkills` for players to refresh their learned skills against the server's current skill data after a TRE update and server restart. It preserves experience and progression while refreshing skill modifiers, abilities, schematics, points, and movement values. A confirmation window precedes the refresh. A successful use starts a persistent 12-hour cooldown for players; game admins are exempt. The user verified the behavior. The command and its name and description are staged for the next update TRE.

### GCW city banner placement corrections

- User-supplied corrections move misplaced Tyrena, Kor Vella, and Mos Eisley banners and fix the cleanup data key. The original GCW startup schedule remains in place.

## 2026-10-01

### Default Galaxy Chat and Auction rooms

- New characters join Galaxy Chat and Auction. Both rooms are restored on every login, including for existing characters whose saved room IDs are missing or stale.

### Structure maintenance and power withdrawals

- Owning-account characters and game admins can withdraw maintenance from non-civic buildings and installations through Structure Management, directly below Pay Maintenance. Powered installations also offer Withdraw Power beside Deposit Power. Both use sliders. Power returns as a generic Stored Power resource container that can be deposited again at one unit per power point; its displayed resource name and class use readable labels.

### Committed combined credit payments

- Purchases, fees, fines, maintenance, repairs, bets, city tax, and selected scripted payments can now use cash and bank together. Each payment retains its prior primary source and uses the other balance for any shortfall. Player trades and tip choices remain unchanged.

### Committed player-city bank terminals

- Corellia, Naboo, and Tatooine player-city bank templates now have two outer bank terminals and a middle bazaar terminal. Existing banks must be redeeded and placed again to receive the change.

### Committed city trainer renaming

- Mayors and game admins can rename recruited city trainers, faction recruiters, and SpyNet informants from their radial. Their role stays in parentheses after the personal name, including on repeated renames. SpyNet informants now receive a random personal name with “(a SpyNet operative)” wherever they spawn, including NPC cities. The recruitment list calls these choices **SpyNet operative (Informant)**, **Rebel (Recruiter)**, and **Imperial (Recruiter)**. The rename option is absent from ordinary NPC-city trainers because it requires membership in the city's saved recruited-trainer list.

### Committed single city trainer removal

- The City Management trainer list now has a **Remove** button beside the existing waypoint action. It confirms the selected NPC and deletes only that city's registered trainer from the world and database. Mayor/admin authority and trainer membership are checked again on confirmation.

### Committed city trainer management and placement direction

- Mayors and game admins can list a city's recruited trainers from City Management. The list shows each trainer's building when indoors and its world coordinates; selecting one creates a waypoint. **Clear All Trainers** shows a confirmation listing every trainer it will remove, then deletes only those still registered to that city. Newly recruited trainers now face the player's placement direction consistently.

## 2026-09-30

### Committed structure account admin entry

- Structure administrators can add one persistent `account:<character>` Admin List entry through the existing radial-opened list. Every current and future character on that account receives admin access; removing the entry removes that shared access. Another account token for the same account is rejected, while a separately added character entry remains after account removal. Existing character entries are consolidated when first adding the account. Unknown character names produce a clear error.

### Committed indoor and outdoor city trainer placement

- City trainers, SpyNet informants, and faction recruiters can now be placed outdoors within the mayor's city or indoors in its civic buildings and player cantinas, hospitals, and theaters. Mayors need building administrator access for player buildings; game admins bypass mayor and building-access requirements. Indoor NPCs spawn in the player's cell. The city charges the same 1,000-credit recruitment cost and ongoing upkeep in both locations, and mayors or game admins can remove them. City-radius cleanup now uses world coordinates so an indoor trainer is not mistaken for an out-of-bounds NPC during an update.

### Committed city recruitable NPCs

- Extended `/recruitSkillTrainer` with one SpyNet informant choice plus Rebel and Imperial recruiters. The existing city trainer choices remain. The informant works with all Bounty Hunter investigation levels. These NPCs use city trainer capacity, treasury cost, upkeep, and persistence. Mayors can remove recruited NPCs with the Remove radial; the option is hidden for unrelated NPCs that share an appearance.

### Committed SpyNet informant access

- SpyNet informants now provide bounty investigation information regardless of the informant's old level and the player's investigation level. Bounty Hunter skill and an active bounty mission are still required. Mission progression uses the mission's level so its waypoint behavior remains correct.

### Committed structure item search

- Added **Find Item by Name** to Structure Management in buildings with item storage. An administrator enters a keyword, selects a matching stored item, and moves it to their feet. The search includes items inside containers and limits the result list to 100 entries. Access and item location are checked again when the result is selected.

## 2026-09-29

### Committed account structure list in `/find`

- Added `/find lots` to list structures owned by any character on the account, with assigned lots, maintenance balance, power on installations that consume it, and city treasury where applicable. Generators do not show a power balance. Structures within city limits include the city after their name, such as `City Hall / Chicago`. It also shows total account lots used and available.

### Committed city militia zoning rights

- City militia members now have zoning rights automatically for as long as they serve. Militia members can already use `/grantZoningRights`; the command now explains that temporary grants cannot be toggled for another militia member.

### Committed structure planet placement option

- Added `Core3.StructureManager.AllowPlacementOnAllPlanets = true` to both configuration files. When enabled, structure deeds ignore their template planet lists, and the deed’s “Can Be Built On” detail shows **All Planets**. Turning it off restores the template list and original placement restriction; terrain, zoning, faction, and other placement rules remain.

### Committed city population downgrade override

- Added an admin-only **City Hacks → Ignore Citizen Requirements** toggle, saved on each city and off by default. When on, scheduled city updates do not downgrade the city because its citizen count is below the current rank requirement. It remains enabled across restarts and mayor changes until an admin turns it off. Elections, maintenance, tax processing, population-based advancement, and the admin force-rank action remain available.

### Removal of Codex test scripts and notes

- Removed all 26 Codex-created standalone test scripts from `MMOCoreORB/src/tests/standalone`, plus two Codex-created audit/dependency notes under `MMOCoreORB/bin/docs` that the user removed. Existing project tests and test-named game content remain.

### Committed quick city treasury deposit

- The mayor now has a Quick Options treasury deposit at the city management terminal. Its per-city amount defaults to 100,000 credits, uses a compact radial label such as `100k Treasury Deposit`, and can be changed under City Treasury. Setting it to zero hides the shortcut and Quick Options menu. An existing city displayed an invalid 901.9M amount because old-city loading skipped the initialization path for the new field; a field-level default and load-time range check now protect older cities while preserving valid saved settings, including zero.

### Committed structure quick options

- Added an account-owner Quick Options radial for per-structure quick maintenance, quick power on powered installations, and withdraw-all resources on harvesters and generators. Structure Management lets owning-account characters set separate saved maintenance and power amounts for each structure; both default to 10,000. Setting one to zero hides that shortcut, and Quick Options disappears when it has no actions. Withdraw All Resources remains available on harvesters even when both amounts are zero. Quick menu labels shorten amounts, such as `10k Maintenance` or `100k Power`. Existing admins outside the owning account do not receive these options.
- Moved Operate Machinery to the first main radial position on harvesters and generators, followed by Quick Options and Structure Management. Houses show Quick Options before Structure Management.

### Civic structure status cleanup

- Structure Status no longer adds an empty privileged debug row. Civic structures without a maintenance warning now show no blank line, while actual warnings still appear.

### Committed additional structure storage lots

- Added **Structure Management → Add Storage Lots / Remove Storage Lots** for buildings that already consume lots. Only characters on the owning account receive these options; ordinary structure admins do not. Each option appears only when a valid adjustment is available.
- The add/remove window uses the client's existing transfer slider. Added lots use the shared account allowance and increase storage by the configured `ItemsPerLot`; each building can add at most twice its original lot cost. A two-lot house can therefore have up to four added lots, six total. Players cannot remove a building's base lots or reduce capacity below its current contents. The structure report shows base, added, and total lots alongside storage usage.
- Added lots persist across restarts and ownership transfers. Player-initiated destruction and redeeding cancel while any added lots remain; the player must remove them first. Server cleanup still frees all lots if it destroys a structure. A newly placed deed starts at its normal base cost. Zero-lot buildings retain their configured capacity and have no lot-adjustment menus.

### Committed project guidance update

- The user replaced root `AGENTS.md` with concise workspace, source, commit, testing, and history guidance, and now requires a dependency summary and confirmation before MTGServer ports. A later user edit also prohibited automatic test-file creation without the stated explicit request.

### Committed structure capacity configuration

- Added `Core3.StructureManager.ItemsPerLot = 200`, `NoLotItemCount = 1000`, and `LotsPerCharacter = 10` to both configuration files, preserving the current defaults. Building storage and the structure report use the configured limits; the shared account lot pool uses maximum character slots times `LotsPerCharacter`, plus its admin bonus.
- Zero/negative settings provide zero base capacity, and large calculations avoid integer overflow. Existing items, structures, admin bonuses, and historical lot-bonus migration are preserved when settings change.

### Committed shared account lots and structure permissions

- Replaced separate character lot allowances with a shared account pool in the current galaxy: `Core3.PlayerCreationManager.MaxCharactersPerGalaxy * 10`, plus an account-wide admin bonus. Updated the explanatory comment in both configuration files. `/adjustLotCount` now adjusts the whole account; existing character bonuses migrate once.
- Offline owners count toward the pool. Construction reserves lots and returns them on cancellation/failure; placement, displays, transfers, redeeding, and destruction use the shared balance. Same-account transfers consume no additional lots, even when the pool is full.
- Characters on the owner's account receive owner-level structure management rights, including private-house access, administration, maintenance, installation controls, transferring, redeeding, and destruction. Residence remains with the named owner, as requested; existing no-trade, faction, and civic restrictions remain.
- Added **Structure Management → Take Ownership** for an alt to claim an eligible non-residence house or installation while the named owner is offline. Shared lot usage stays unchanged, and the alt can then declare the house as its residence. Special civic/faction/guild/camp ownership remains separate.
- Destruction confirmations recheck ownership and their original session; pending destruction prevents competing redeeds/transfers. Fixed the reported confirmation freeze by accepting the input window's normal two-field response, clearing invalid-code attempts, and removing stale destruction confirmations on login. Redeeding returns the deed to the acting character while cleanup uses the actual owner's records.

## 2026-09-28

### Committed structure storage limits and reporting

- Building storage now allows 200 items per lot with no separate per-building cap. All zero-lot buildings, including civic structures, allow 1,000 items, as clarified by the user.
- Floor placement and transfers into containers inside buildings use the same updated limit. Existing buildings adopt it after a restart; no TRE update or database migration is needed.
- The building structure report now shows `Storage Used: item count / max storage` on one line, using the same limit and counting methods as storage enforcement. Refresh recalculates both values.

### Committed Medium Corellia House Style 2 schematic

- Added the Medium Corellia House (Style 2) draft schematic to Architect Buildings III. Completed its server recipe using the existing medium Corellian house's materials and 8,000 XP, registered it for crafting, and staged its skill-group assignment in `SWGFR_update_01/datatables/crafting/schematic_group.iff`.
- Added the missing client name and description for the style-2 deed, fixing its unresolved skill-window string references. The name is "Deed for: Medium Corellia House (Style 2)"; the server deed uses the same name.
- Diagnosed an unnamed admin-generated deed as a deployment issue: the installed server update TRE lacked both new deed string tables, so `/object createitem` saved only " (System Generated)".

### Committed SWGFR staff tags

- Changed all 12 active elevated-player tag definitions from `SWGEmu-` to `SWGFR-`, retaining their role suffixes, such as `SWGFR-Admin`, `SWGFR-Dev`, and `SWGFR-CSR`. Character, chat, and ship displays use these shared definitions.

### Committed faction rank limits from TRE data

- Recruiter promotions and the admin `/setFaction` rank limit now follow the loaded `datatables/faction/rank.iff` instead of stopping at rank 15, Colonel. The active TRE table has 22 ranks, ending at rank 21, Surface Marshal, making six additional ranks attainable with their existing faction-point costs.
- Recruiter confirmation and acceptance recheck the limit and reject invalid next-rank costs, preventing an outdated promotion conversation from assigning a rank beyond the table or charging points for it. Existing faction-point minimums and rank benefits remain unchanged.

## 2026-09-27

### Committed character tutorial room and item-box fix

- Corrected two misspelled room-name checks that made the tutorial ignore the player's current room and completed rooms. This restores the introductory sequence and the officer-conversation step that grants access to the starting-item box.

### Committed helper droid configuration and login lifecycle

- Added `Core3.HelperDroid.Enabled` and `Core3.HelperDroid.AutoCallOnZone` together in both configuration files, with shared defaults enabled and the user's local settings preserved. With zone auto-calls off, the initial planet arrival and six novice-profession triggers still call the helper; later login/travel/zoning does not recall it. Existing age limits apply to those automatic summons.
- When disabled, login now removes the helper and its datapad device, clears its ship assignments, and preserves quest progress. When enabled, a missing helper is restored on login as a stored device, including for older characters, unless that player manually deleted it. Manual deletion prevents automatic replacement; older characters without deletion history receive a stored helper.

### Committed Empty Mail Target command-browser assets

- Added the missing English `cmd_n:emptymailtarget` name, **Empty Mail Target**, and `cmd_d:emptymailtarget` description explaining mailbox deletion for a selected player or specified first name, with `/emptyMail` for the admin's own mailbox.
- Assigned the existing mail-envelope icon to the command in both ground and space UI styles. All three client files are staged only in `SWGFR_update_01`; no new texture or server behavior change is needed.

### Committed admin skill revocation selection and confirmation

- `/revokeSkill` now opens an alphabetical skill list for the targeted player, or for the admin issuing the command when no target is selected. Invalid explicit targets are rejected. `/revokeSkill all` previews all revocable skills for either target choice.
- Selecting a skill previews its learned dependents and the returned skill points before confirmation. Both lists are alphabetical. The window identifies and retains the original player, and changed skill plans require another confirmation.
- Admin access is checked when the command starts and again during selection/confirmation. Pilot revocation remains available to admins; innate, language, staff, and protected progression skills remain. The shared eligibility check explicitly protects Force ranking skills against unlisted rank-removal effects.

### Committed skill surrender selection and confirmation

- `/surrenderSkill` now lists learned skills that can be surrendered. Both the selection and confirmation lists are alphabetical by skill display name, ignoring capitalization. Selecting a skill previews that skill and every learned skill that requires it, including dependent professions. Selecting Novice Entertainer therefore includes its learned Entertainer, Dancer, and Musician dependents.
- The confirmation lists all planned removals and the skill points to recover. Cancel keeps every skill. `/surrenderSkill all` previews all currently surrenderable skills through the same confirmation flow; innate, language, staff, pilot, and protected progression skills remain.
- Removal follows prerequisite order and uses the existing surrender behavior for refunds, abilities, modifiers, and schematics. Changed skill lists require another confirmation, and Jedi progression requirements are checked against the complete plan before surrender starts. Zero-point profession boxes are included.

### Committed shutdown session disconnect and login logging fixes

- Fixed shutdown walking the online-account map while each disconnect changes that same map, which could skip other connected players. Shutdown now captures all player sessions first and releases the map lock before disconnecting them, including multiple accounts or characters sharing one IP.
- The initial disconnect message now counts sessions rather than accounts. The existing wait reports a warning if players remain connected instead of always reporting success. Logout behavior, the wait duration, and final save/cleanup ordering are preserved.
- The console could show only three logged-in players because the fourth login arrived within the existing five-second console-summary throttle. A separate three-player shutdown snapshot could appear after the first player was marked offline. The message now says `Online player snapshot: N players currently online` to clarify its meaning.
- Completed logins now force an immediate console snapshot, including logins less than five seconds apart or with an unchanged total. Normal status updates retain the throttle, and session-change file logging still follows its existing setting.
- Normal shutdown now forces the full online snapshot before the disconnect-start messages and suppresses intermediate shutdown snapshots on the console. File records and statistics continue updating during each logout.

### Committed shutdown cleanup improvement

- Corrected ground and space cleanup to remove the departing object from nearby-object lists. The previous calls targeted the zone instead, leaving the object's list populated and causing repeated scans.
- Limited cleanup through a parent's nearby-object list to one pass while preserving the parent's relationships. Objects with their own lists retain the existing cleanup retries. The full save, player disconnection, shutdown ordering, and remaining object cleanup are unchanged.

### Committed vehicle recovery fix

- Fixed a database-load race that could put a vehicle back into the world after login had already stored it and cleared its owner link. Deferred insertion now checks that the object still belongs to the saved zone and has not already been inserted.
- Existing affected vehicles with intact datapad references can use the normal login storage and subsequent call path to recover.

### Committed configuration cleanup

- Audited main configuration consumers in `src` and `bin`, then organized both Lua config files into matching sections. Each now documents 150 active settings, 15 optional overrides, and five dynamic key families. Added missing source-backed settings, removed seven unused entries, and renamed `DeleteCharacters` to `PurgeDeletedCharacters`.
- The user restored the commented TEST-zone options in both configurations: 17 ground zones and six space zones. They remain disabled; the enabled-world lists are unchanged.
- Corrected the orphan-removal spelling, victim-list namespace, and ship AI logging reader. Legacy aliases remain supported. Preserved existing effective settings and private local values; the local file stays ignored.

### Committed startup and asset changes

- Reviewed 11 user-added assets in `SWGFR_update_01`: a pilot-chair template, six empty ship-table placeholders, and four populated ship tables. The chair references an existing pilot-station slot descriptor; the four populated tables still require 45 missing client attachments and matching server definitions. Preserved all additions and documented their limitations.
- Added the remaining working-directory `bin/engine3.lua` entry point without settings, preserving engine defaults.
- Corrected ship loading to skip component tables for chassis without component slots.

## 2026-09-26

### Committed startup and asset changes

- Corrected optional configuration loading, an obsolete city setting, resource/station template types, and misleading particle-appearance diagnostics.
- Restored the missing vehicle-component base, two appearance redirects, and 12 ship component tables from existing authorized MTG archives, stored only in `SWGFR_update_01`. Consolidated duplicate ship-data reads and corrected appearance-slot mapping for sparse ship tables.
- Recorded the asset-staging preference and removed all 15 duplicate loose assets from `bin`. Added `SWGFR_update_01.tre` first in both Lua configurations and aligned ConfigManager's latest-TRE default.

### Previously committed changes

- Clarified project guidance: MTGServer is an authorized source for relevant fixes and content; importing from unauthorized projects or branches remains prohibited. Commit requests require reviewing outstanding checks unless the user explicitly waives them.
- Created `MMOCoreORB/bin/conf/config-local.lua` as a local copy of `config.lua`. Existing Git ignore rules keep it untracked.
- Added ignore rules for the local `swgemu-SWGFR.sql` and `mantis-SWGFR.sql` files. Both were already untracked and remain present locally, unchanged.
- Removed the generated `MMOCoreORB/bin/scripts/managers/resource_manager_spawns.lua` from Git tracking and deleted the old local copy. Core3 regenerates it; the file remains ignored and untracked.
