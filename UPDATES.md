# Project Updates

## 2026-09-26

### Committed changes

- Clarified project guidance: MTGServer is an authorized source for relevant fixes and content; importing from unauthorized projects or branches remains prohibited. Verification records must distinguish static checks from user-confirmed Core3 builds and runtime testing. Commit requests now require reviewing verification and resolving outstanding checks unless the user explicitly requests a commit without verification.
- Created `MMOCoreORB/bin/conf/config-local.lua` as an exact copy of `config.lua` for local configuration. Verified that the existing Git ignore rules exclude it and that it is not tracked.
- Added ignore rules for the local `swgemu-SWGFR.sql` and `mantis-SWGFR.sql` files. Both were already untracked and remain present locally, unchanged.
- Removed the generated `MMOCoreORB/bin/scripts/managers/resource_manager_spawns.lua` from Git tracking and deleted the old local copy. The user confirmed full Core3 startup; verified that the file regenerated with resource entries and remains ignored and untracked.
