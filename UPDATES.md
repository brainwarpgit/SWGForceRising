# Project Updates

## 2026-09-27

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
