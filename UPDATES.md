# Project Updates

## 2026-09-27

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
