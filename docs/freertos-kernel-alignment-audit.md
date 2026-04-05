# FreeRTOS Kernel Alignment Audit

## Scope

This note records the result of primitive issue `#29`, which aligns only
`freertos_kernel/` against the `iot-reference-rx`
`v202406.01-LTS-rx-1.1.1` baseline.

## Reference Used

- `iot-reference-rx` tag: `v202406.01-LTS-rx-1.1.1`
- pinned kernel submodule commit:
  `cb692f1dd33138eb2c44b20a3168fb79c84f5dbb`

Observed reference-kernel state:

- `manifest.yml`: `V11.0.1+`
- `include/task.h`: `tskKERNEL_VERSION_NUMBER == "V11.1.0+"`

## Current Repository State Before This Primitive

The current repository already carried:

- `freertos_kernel/manifest.yml`: `v11.1.0`
- `freertos_kernel/include/task.h`: `tskKERNEL_VERSION_NUMBER == "V11.1.0"`

So the repository was already on a released `11.1.0` kernel tree, while the
reference repository's pinned kernel had drifted to a development-branch
variant.

## Decision

Do not replace the entire `freertos_kernel/` tree with the reference submodule
contents in this primitive.

Reason:

- the full tree diff is very large and includes many unrelated upstream changes
- this primitive is intentionally limited to kernel-only changes with minimal
  fallout
- the migration target fixed by the current project policy is the stable
  `iot-reference-rx` baseline, not an opportunistic jump to every newer
  development-branch kernel change

Instead, adopt only the RX700v3 / CCRX-specific fixes from the reference fork
that materially affect RX72N behavior.

## Changes Taken

### 1. RX700v3 DPFPU stack layout fix

File:

- `freertos_kernel/portable/Renesas/RX700v3_DPFPU/port.c`

Imported behavior:

- stop seeding the extra A0 low-word placeholder during initial stack creation
- stop saving the A0 low word in the context-save path

Why:

- the reference fork documents that CCRX restores the first task through
  `com_opt4`
- that helper injects a return address into the lowest restored slot before the
  final `RTE`
- matching that restore order avoids misalignment of FPSW / R1 / PC / PSW on
  RX700v3 DPFPU tasks

### 2. Assert guard normalization

File:

- `freertos_kernel/portable/Renesas/RX700v3_DPFPU/portmacro.h`

Imported behavior:

- use `#if ( configASSERT_DEFINED == 1 )` instead of `#ifdef configASSERT`

Why:

- this matches current upstream FreeRTOS kernel conventions
- it avoids relying on whether `configASSERT` is defined as a macro symbol in a
  particular translation unit layout

## Changes Explicitly Not Taken

- global kernel version string change from `V11.1.0` to `V11.1.0+`
- unrelated upstream kernel drift outside the RX700v3 path
- changes in other middleware or project configuration

Those belong to later primitives if they become necessary.
