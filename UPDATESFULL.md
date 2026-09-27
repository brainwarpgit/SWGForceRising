# Detailed Project Updates

## 2026-09-26

### Committed changes

#### Source authorization and verification records

- Updated `AGENTS.md` to prohibit importing fixes, source changes, or other content from unauthorized projects or branches, while explicitly authorizing MTGServer as a source for relevant fixes and content. MTGServer remains read-only, imports must stay within the task scope, and content ports must follow the existing porting rules.
- Clarified that update histories must record the verification performed and distinguish static checks from user-confirmed Core3 builds and runtime testing.
- Added a commit verification requirement: review the intended changes and applicable prior verification, complete permitted checks, and give the user a checklist of any remaining checks with expected results. Commits wait for necessary verification to pass; when nothing remains, proceed with the authorized commit without another confirmation. A commit request alone does not authorize a Core3 build or run.
- An explicit request to commit without verification bypasses the verification review, checklist, and testing for that commit and proceeds without another confirmation. Git state is still inspected as needed to include only the intended changes. Record verification as skipped at the user's request rather than passed.
- Created the short and detailed update histories, which were not previously present, to record this standing guidance change.
- Verification: Reviewed the wording and checked the changed documentation for whitespace issues. This documentation change requires no deployment or Core3 testing.

#### Local server configuration

- Created `MMOCoreORB/bin/conf/config-local.lua` as an exact copy of `MMOCoreORB/bin/conf/config.lua`, providing a local configuration file without changing the tracked source configuration.
- The existing `bin/conf/*` rule in `MMOCoreORB/.gitignore` already excludes the local file, so no ignore-rule change was needed. The local file remains untracked and ignored.
- Verification: Initially confirmed byte-for-byte equality with `cmp`, confirmed the matching ignore rule with `git check-ignore -v`, and checked that Git reports the file as ignored and does not list it among tracked files. The user subsequently confirmed full Core3 startup after these changes; the assistant did not build or run Core3.

#### Local SQL files excluded from Git

- Added filename-specific rules in `MMOCoreORB/sql/.gitignore` for `swgemu-SWGFR.sql` and `mantis-SWGFR.sql` so ordinary Git adds exclude these local files.
- Both SQL files were already untracked, so no index removal was necessary. Neither SQL file was modified or deleted.
- Verification: Confirmed both files remain present locally, `git ls-files` lists neither file, and `git check-ignore -v` and `git status --ignored` identify both as ignored. This Git-only change required no Core3 build, runtime test, or database operation.

#### Generated resource spawn configuration

- Removed `MMOCoreORB/bin/scripts/managers/resource_manager_spawns.lua` from Git tracking and deleted its old local copy as requested. The actual directory is `scripts/managers`, with a plural name. Core3 has since regenerated the local file, which remains ignored and untracked.
- Added a filename-specific rule to `MMOCoreORB/bin/.gitignore` so the regenerated resource spawn file stays out of ordinary Git adds.
- Static source review confirms that startup updates resource pools and writes this file when `buildInitialResourcesFromScript` is enabled, as it currently is in `resource_manager.lua`. With an empty resource database, the missing file can produce an `Invalid script` log before the startup flow proceeds to generate and save resources.
- Verification: Reviewed the startup and file-writing paths and initially confirmed the local deletion. The user subsequently confirmed full Core3 startup. Before committing, verified that the regenerated file is nonempty and contains resource type and name entries, `git ls-files` no longer lists it, and `git check-ignore -v` matches the new rule. Whitespace checks passed. The assistant did not build or run Core3; no necessary verification remains outstanding for this cleanup.
