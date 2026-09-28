# Project Updates

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
