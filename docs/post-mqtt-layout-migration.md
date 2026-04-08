# Post-MQTT Layout Migration

## Goal

Migrate the current RX72N repository from the legacy top-level tree:

- `projects/`
- `vendors/`
- `libraries/`
- `freertos_kernel/`
- `demos/`
- `test_scripts/`
- `tools/`

toward the post-MQTT target structure aligned with the `iot-reference-rx`
style:

- `Common/`
- `Configuration/`
- `Demos/`
- `Middleware/`
- `Projects/`
- `Test/`

This issue does not require a single-step move. The migration is intentionally
split into small, reviewable changes that preserve the current MQTT-green
baseline.

## Constraints

- Start from `master`, not from historical `phase8b/`.
- Keep the current custom RX72N boot path unchanged during layout work.
- Keep the current runtime gate at least MQTT-green after each move set.
- Do not mix Fleet Provisioning, OTA protocol changes, or MCUboot adoption into
  this track.

## Rename Safety Constraint

This repository is currently operated on Windows with `core.ignorecase=true`.
That means case-only transitions such as `projects/` -> `Projects/` and
`demos/` -> `Demos/` are not safe as a one-step rename in the first move set.

When those top-level transitions start, use one of these approaches:

- rename through a temporary intermediate directory name,
- perform the rename in a case-sensitive environment,
- or land content under a non-colliding target path until the legacy tree is
  retired.

This track intentionally restarts from `master`, but it still has to preserve
the rename-safety discipline that the earlier `phase8b/` staging work made
explicit.

## Current Mapping

The current tree is functionally close to these target buckets:

| Current path | Target bucket | Notes |
|--------------|---------------|-------|
| `vendors/renesas/boards/rx72n-envision-kit/` | `Projects/` + `Configuration/` | Board app, config, and board-specific ports are mixed together today |
| `libraries/` | `Middleware/` | Third-party and AWS/FreeRTOS libraries |
| `freertos_kernel/` | `Middleware/` | Kernel stays separate today, but belongs in the middleware layer conceptually |
| `demos/` | `Demos/` | Demo sources already map cleanly |
| `projects/renesas/rx72n_envision_kit/e2studio/` | `Projects/` | e2studio projects are already grouped here |
| `test_scripts/` + `tools/ci/` | `Test/` | CI helpers and hardware tests |

## Migration Strategy

### Phase 1: Documentation and path freeze

- Document the target layout and the current-to-target mapping.
- Identify which paths are runtime-critical and must not move first.
- Freeze naming for the target top-level directories.

### Phase 2: Non-runtime test/tool moves

- Move low-risk `Test/` candidates first.
- Prefer wrappers, path shims, or import compatibility where needed.
- Keep CI green before moving runtime-sensitive trees.

### Phase 3: Demo and middleware normalization

- Separate `Demos/` and middleware-oriented content from board application
  code.
- Reduce path coupling in scripts and project metadata before any large tree
  move.

### Phase 4: Project/config split

- Split board/application content into `Projects/` and `Configuration/`
  oriented locations.
- Only move runtime-sensitive paths after the path consumers are already
  decoupled.

## First Reviewable Move Candidates

The first code changes under this issue should prefer items with low runtime
risk:

1. Document the target layout and move sequence.
2. Migrate path references in CI/test helpers away from hard-coded legacy
   top-level assumptions.
3. Move clearly test-only material under a `Test/` landing zone.

Large moves of board runtime code should be deferred until path consumers are
already insulated.

## Exit Criteria

This issue is complete when:

- the target layout is documented and agreed,
- the moved tree still headless-builds,
- and the runtime baseline remains at least MQTT-green after the applied move
  set.
