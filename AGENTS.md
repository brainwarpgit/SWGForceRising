# Running Project Guidance
# CRITICAL: Minimize output token length to conserve API credits. No pleasantries. Output only diffs or targeted code blocks, never entire unchanged files.

# Workspace Paths
- Read/Write Primary: `/home/swgemu/workspace/SWGForceRising`
- Read-Only Reference: `/home/swgemu/workspace/MTGServer` (Never modify)
- Read-Only Clients: `/home/swgemu/workspace/tre` (Never modify)
- Read/Write Assets: `/home/swgemu/workspace/SWGForceRising/SWGFR_update_01` (Preserve relative paths)
- Read-Only Extracted: `/home/swgemu/workspace/extracted-SWGFR`
- Read-Only Extracted Reference: `/home/swgemu/workspace/extracted-MTG`

## Workspace Boundaries
- Normal work must stay within: `MMOCoreORB/bin` and `MMOCoreORB/src`
- Permitted read/search exceptions: `MTGServer`, `tre`, `extracted-SWGFR`, `extracted-MTG`
- Permitted read/write exceptions: `SWGFR_update_01`, `AGENTS.md`, `UPDATES.md`, `UPDATESFULL.md`
- Do not access other locations unless explicitly asked.

## Client Asset Staging
- Create/update client asset files ONLY in `SWGFR_update_01`. Do not create loose copies under `MMOCoreORB/bin`.
- Server Lua scripts and source changes belong in `MMOCoreORB/bin/scripts` and `MMOCoreORB/src`.
- Keep `SWGFR_update_01.tre` entry first in `config.lua` and `config-local.lua` TRE lists.

## Protected Dependencies
- `MMOCoreORB/utils/engine3` submodule is immutable. Never edit, patch, format, replace, or generate files within it.
- Implement source fixes outside the submodule. Do not use a submodule revision change as a workaround.

## Source Provenance
- Do not import fixes/content from unauthorized projects or branches.
- MTGServer is authorized for comparison and porting. Keep it read-only.
- Develop fixes from the currently checked-out branch.

## Git Commits
- Do not create commits unless explicitly asked.
- Before committing (unless skipped by user), review changes against verification records. Provide a concrete checklist of remaining validation (static, build, runtime, in-game).
- Wait for passing results or explicit bypass. Do not commit while verification is pending/failing.
- If user requests to skip verification, proceed immediately without a checklist. Record verification as "skipped", not "passed".

## Building, Running, and Testing
- CRITICAL TOKEN DEFENSE: Do not automatically write unit tests, test scripts, or mock data files for the code you generate.
- Only write functional logic, scripts, or diffs.
- You are strictly forbidden from creating test files unless the user explicitly uses the phrase "write a test script for this".
- Do not compile Core3, link/install a rebuilt executable, or run `core3` (including GDB/`runUnitTests`) unless explicitly requested.
- Perform maximum validation within allowed folders before that point: check diffs, whitespace, and use static syntax checks.

## Maintaining History & Guidance
- Update this file when standing project guidance changes.
- Keep `UPDATES.md` (short, plain-language updates) and `UPDATESFULL.md` (expanded high-level history with context/reasons) current. Update both in the same change as the implementation.
- Distinguish committed from uncommitted changes. Do not present proposals as completed.
- User testing / verification / other message should be in `UPDATESFULL.md` never in `UPDATES.md`.

# Porting Rules (MTGServer to SWGForceRising)
1. Locate implementation in MTGServer.
2. Identify server dependencies (Lua, screenplay, templates, loot, mobiles, conversations, quests, C++).
3. Identify client dependencies (.iff, .msh, .apt, .sat, .lod, .dds, .sht, .tga, .tre).
4. Compare dependencies against existing SWGForceRising client TRE files.
5. Only extract/copy client assets that do not exist.
6. Create/adapt required Lua files for SWGForceRising.
7. Do not import unrelated content. Preserve SWGForceRising conventions.
8. STOP: Present a minimalist summary of dependencies and proposed changes. Wait for user confirmation before generating code.