# Running Project Guidance

These instructions apply throughout this project. Paths below are relative to the repository root.

# Workspace and Reference Directories

The following are absolute paths within the development workspace.

- `/home/swgemu/workspace/SWGForceRising`
  - Primary project.
  - Read/write.

- `/home/swgemu/workspace/MTGServer`
  - Secondary reference project.
  - Read-only.
  - Never modify files in this repository.

- `/home/swgemu/workspace/tre`
  - Primary SWGForceRising/client TRE archive collection.
  - Read-only.
  - Never modify existing TRE archives here unless explicitly requested by the user.

- `/home/swgemu/workspace/SWGForceRising/SWGFR_update_01`
  - Source tree for new or corrected client files intended for the SWGForceRising update TRE.
  - Read/write.
  - Preserve archive-relative paths.

- `/home/swgemu/workspace/extracted-SWGFR`
  - Extracted contents of the primary SWGForceRising client TRE set.
  - Read-only reference.
  - Never modify.

- `/home/swgemu/workspace/extracted-MTG`
  - Extracted contents of the MTGServer client TRE set.
  - Read-only reference.
  - Never modify.

## Workspace boundaries

- Normal SWGForceRising project work must stay within:
  - `MMOCoreORB/bin`
  - `MMOCoreORB/src`

- The following locations are explicitly permitted exceptions:

  - `/home/swgemu/workspace/MTGServer`
    - Read/search only when comparing or porting content from MTGServer.

  - `/home/swgemu/workspace/tre`
    - Read/search only for examining the primary client TRE archives.

  - `/home/swgemu/workspace/extracted-SWGFR`
    - Read/search only for determining whether client assets already exist.

  - `/home/swgemu/workspace/extracted-MTG`
    - Read/search only for locating MTG-specific client assets and their dependencies.

  - `/home/swgemu/workspace/SWGForceRising/SWGFR_update_01`
    - Read/write.
    - Store new or corrected files intended for the SWGForceRising update TRE here.

- The repository root `AGENTS.md`, `UPDATES.md`, and `UPDATESFULL.md`
  are also permitted read/write exceptions for maintaining project guidance
  and project history.

- Do not access other locations unless the user explicitly asks.

## Protected dependencies

- Treat the contents of the `MMOCoreORB/utils/engine3` submodule as immutable. Never edit, patch, format, replace, or generate files within it as part of a project fix or change.
- Implement source fixes outside the engine3 submodule and within the authorized workspace boundaries. Do not use a submodule revision change as a workaround for a project source issue.
- An engine3 revision or recorded-pointer update is permitted only when the user explicitly requests an upstream dependency alignment or update. Use an unmodified commit from the configured upstream branch, and do not include engine3 source changes.

## Source provenance

- Do not import fixes, source changes, or other content from unauthorized projects or branches, including by cherry-picking, copying, or recreating their patches.
- MTGServer is an authorized source for comparison and for importing relevant fixes or content. Keep MTGServer read-only, stay within the task scope, and follow the porting rules below when porting content.
- Develop fixes from the currently checked-out branch and authorized reference sources; do not use other projects or branches unless the user authorizes them.

## Git commits

- Do not create commits unless the user explicitly asks you to commit.
- For every commit request, unless the user explicitly asks to skip verification, review the changes intended for that commit and the existing verification records. Determine whether the changes have been verified to work and identify any relevant static, build, runtime, or in-game checks that remain. Static checks alone do not establish that runtime behavior works.
- Complete the checks permitted by the existing project instructions, then give the user a concrete checklist of any remaining verification, including what to check and the expected results. Do not commit while necessary verification is pending or failing; wait for passing results or an explicit instruction to commit without verification.
- Reuse verification that still applies to the current changes. If no necessary verification remains, state that and proceed with the requested commit without asking for another confirmation.
- If the user explicitly says to commit without verification, skip the verification review, checklist, and testing for that commit and proceed without another confirmation. Still inspect Git state as needed to include only the intended changes. Record verification as skipped at the user's request, not as passed.
- A commit request by itself does not authorize building or running Core3; the existing build and run restrictions still apply.

## Building, running, and testing

- Leave building and running Core3 to the user. The user will report build errors, warnings, and runtime errors for investigation.
- Do not compile Core3 or its components, link or install a rebuilt executable, or run `core3`, including under GDB or through `runUnitTests`, unless the user explicitly requests it.
- Perform as much relevant validation as possible before that point, within the allowed folders: review changes and callers, check diffs and whitespace, use available syntax or static checks, and run standalone tests that do not build or execute Core3.

## Maintaining this guidance

- Keep this root file as the single running record of project instructions and preferences provided by the user.
- Update it when the user adds or changes standing project guidance.

## Maintaining the update history

- Keep `UPDATES.md` and `UPDATESFULL.md` current as project work progresses.
- `UPDATES.md` is the short, plain-language list of meaningful Core3 and related server/client content updates.
- `UPDATESFULL.md` is the expanded high-level history: explain what changed, why it matters, relevant commands or configuration options, and any remaining deployment or testing work. Summarize related fixes together rather than listing every edited file.
- Update both files in the same working change as each meaningful feature, fix, content change, removal, or standing workflow change.
- Record actual implemented work and distinguish committed changes from uncommitted changes. Do not present a proposal, reverted experiment, or unresolved issue as a completed feature.
- Use dated sections, preserve earlier history, and update an existing entry when refining the same change. Identify related user-supplied asset or configuration changes when relevant, without including private local settings or secrets.
- Keep these files synchronized with each other and the final implementation. Maintaining them does not authorize a Git commit or a Core3 build/run.
- Record the verification performed, distinguishing static checks from user-confirmed Core3 builds and runtime testing.

# Porting rules

When asked to port content from MTGServer to SWGForceRising:

1. Locate the implementation in MTGServer.
2. Determine every server-side dependency:
   - Lua files
   - screenplay includes
   - object templates
   - loot groups
   - mobile templates
   - conversations
   - quest data
   - C++ dependencies if any

3. Determine every client-side dependency referenced by the content:
   - .iff
   - .msh
   - .apt
   - .sat
   - .lod
   - .dds
   - .sht
   - .tga
   - .stf
   - .tre references

4. Compare those dependencies against the existing SWGForceRising/client TRE files.

5. Only extract/copy client assets that do not already exist.

6. Create or adapt the required Lua files for SWGForceRising.

7. Do not import unrelated MTGServer content.

8. Preserve SWGForceRising conventions and directory structure wherever possible.

9. Before making changes, show the dependency list and proposed files to add/modify.