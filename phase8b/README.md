# Phase 8b Staging Area

This directory is the non-destructive landing zone for the RX72N migration to the
`iot-reference-rx` baseline.

Why this exists:
- the current repository still has the legacy lower-case tree at the top level
- this repository is often operated on Windows with `core.ignorecase=true`
- case-only transitions such as `projects` -> `Projects` are therefore unsafe as a
  first move

During Phase 8b-1, the new layout is prepared under `phase8b/`.
Once the migrated baseline is stable, the final top-level consolidation can be handled
as a separate change.

Related issues:
- Parent: #11
- Current step: #7
- Next steps: #8, #9, #10, #12
