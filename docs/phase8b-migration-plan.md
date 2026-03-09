# Phase 8b Migration Plan

## Goal

Port `rx72n-envision-kit` from the legacy Amazon FreeRTOS style tree to the
latest `iot-reference-rx` baseline that was already validated in Phase 8a.

Target source baseline:
- `iot-reference-rx` `v202406.01-LTS-rx-1.1.1`
- FreeRTOS Kernel 11.1.0
- FreeRTOS-Plus-TCP 4.2.2
- coreMQTT 2.3.1
- mbedTLS 3.6.3
- littlefs 2.5.1
- `r_fwup` 2.04

## Why This Must Be Staged

The current RX72N repository combines three categories of logic:
- legacy Amazon FreeRTOS tree and middleware placement
- RX72N Envision Kit specific hardware and GUI code
- CI/CD automation for flash, MQTT, SD update, and OTA

Replacing all of them at once would make failures hard to attribute.
The migration therefore proceeds from headless baseline to user-facing features.

## Planned Issue Split

| Step | Issue | Scope |
|------|-------|-------|
| 8b-0 | #11 | Parent tracking issue |
| 8b-1 | #7 | Skeleton import and repo layout preparation |
| 8b-2 | #8 | RX72N boot loader port |
| 8b-3 | #9 | RX72N application port and MQTT baseline |
| 8b-3b | #13 | phase8b hardware baseline CI hookup (`build -> flash -> provision -> MQTT`) |
| 8b-4 | #10 | OTA recovery on the new stack |
| 8b-5 | #12 | GUI / SD update / Envision Kit UX reintegration |

## Current Tree vs Target Tree

Current legacy tree:
- `projects/`
- `vendors/`
- `libraries/`
- `freertos_kernel/`
- `demos/`

Target tree aligned with `iot-reference-rx`:
- `Common/`
- `Configuration/`
- `Demos/`
- `Middleware/`
- `Projects/`
- `Test/`

Important: this is not just a directory rename. Project contents, middleware
references, and Smart Configurator outputs also change.

## Phase 8b-1 Staging Root

Because this repository is currently handled on Windows with `core.ignorecase=true`,
the initial landing zone is created under `phase8b/` instead of the top level.

The first staging layout is:
- `phase8b/Common/`
- `phase8b/Configuration/`
- `phase8b/Demos/`
- `phase8b/Middleware/`
- `phase8b/Projects/`
- `phase8b/Test/`

This allows the new skeleton to be assembled without colliding with the existing
top-level `projects/`, `vendors/`, `libraries/`, and `freertos_kernel/` trees.

## Initial Project Targets

The first new projects should be based on the validated `iot-reference-rx`
Ethernet path and renamed for RX72N:
- `Projects/aws_ether_rx72n_envision_kit/e2studio_ccrx`
- `Projects/boot_loader_rx72n_envision_kit/e2studio_ccrx`

Expected first-pass focus:
- RXv3 + DPFPU FreeRTOS port assumptions
- RX72N dual-bank flash map
- Ethernet PHY and pin configuration
- `r_fwup` RX72N settings
- UART / provisioning / OTA hooks already used by CI/CD

## Validation Gates

1. Build-only gate
   - boot loader and app both build headless
2. Hardware baseline gate
   - flash, provision, and MQTT pass on CI/CD
3. OTA gate
   - `prepare_ota -> ota_create_job -> ota_monitor -> ota_finalize` passes
4. UX gate
   - GUI and SD update features are reattached

## Non-Goals for The Initial Port

- Do not mix MCUboot migration into the first FreeRTOS baseline port
- Do not require GUI recovery before MQTT/OTA baseline is green
- Do not delete the legacy tree until the new path is proven

## Windows Case-Sensitivity Constraint

This repository is currently operated on Windows with `core.ignorecase=true`.
That means case-only transitions such as:
- `projects` -> `Projects`
- `demos` -> `Demos`

are not safe to treat as trivial renames in the first step.

When top-level migration starts for real, use one of these approaches:
- rename through a temporary intermediate name
- perform the rename in a case-sensitive environment
- keep the old tree until the new tree is stable, then remove it in a later change

This is why Phase 8b-1 first uses a `phase8b/` landing zone and imports the
validated upstream baseline there before RX72N-specific porting starts.

## Phase 8b-1 Current Deliverables

- `phase8b/Common/`, `Configuration/`, `Middleware/`, and `Test/` seeded from
  `iot-reference-rx`
- `phase8b/Demos/` seeded from `iot-reference-rx`
- app seed under `phase8b/Projects/aws_ether_rx72n_envision_kit/`
- boot loader seed under `phase8b/Projects/boot_loader_rx72n_envision_kit/`
- upstream inventory documented in `phase8b/UPSTREAM_BASELINE.md`

These imported seeds are intentionally not treated as fully validated RX72N
projects yet. Issue `#8` is the first porting gate and now has a passing
headless boot loader build.

## Phase 8b-2 Current Status

Current result for Issue `#8`:
- `phase8b/Projects/boot_loader_rx72n_envision_kit/e2studio_ccrx`
  builds headless with e2studio 2025-12 + CC-RX and emits `.mot`
- RX72N-specific BSP / flash / SCI / pin configuration was imported from the
  legacy RX72N boot loader
- project metadata was retargeted from RX65N to RX72N (`RXv3 + DPFPU`)
- `r_fwup` area settings were aligned to the RX72N dual-bank layout

Known limitations before hardware validation:
- `R_BSP_ClockReset_Bootloader()` is temporarily treated as a no-op on RX72N
  to unblock the first build gate
- linker warnings still match the legacy RX72N boot loader section layout and
  are not yet cleaned up because they were not build blockers

## Phase 8b-3 Current Status

Current result for Issue `#9`:
- `phase8b/Projects/aws_ether_rx72n_envision_kit/e2studio_ccrx`
  builds headless with e2studio 2025-12 + CC-RX and emits `.abs`, `.mot`, and `.x`
- project metadata was retargeted from RX65N to RX72N (`RXv3 + DPFPU`)
- RX72N-specific BSP / Ethernet / flash / S12AD / SCI / pin configuration was
  imported into the new baseline project
- `BSP_CFG_MCU_PART_FUNCTION`, PPLL clock settings, expansion RAM handling, and
  `BSP_MCU_TFU_VERSION` were aligned to the RX72N environment
- littlefs headers were adjusted so the imported FSP-style interfaces build in
  the RX FIT-based tree
- linker settings were extended for `D_8/R_8` and `DEXRAM_8/REXRAM_8`, which
  removed the previous expansion RAM build blocker

Known limitations before hardware baseline:
- `r_tsip_rx` is still using the imported RX65N target tree and needs formal
  RX72N alignment before the port can be called complete
- linker warnings remain for `C_LITTLEFS_MANAGEMENT_AREA`,
  `C_FIRMWARE_UPDATE_CONTROL_BLOCK`, `C_FIRMWARE_UPDATE_CONTROL_BLOCK_MIRROR`,
  and `C_USER_APPLICATION_AREA`
- there are non-blocking warning groups around generated RX72N mapped interrupt
  macros and SCI feature defines that should be cleaned up after the build gate
- `.gitlab-ci.yml` legacy path still drives the hardware baseline, so phase8b
  is limited to the new Windows build-only gate until flash/provision/MQTT are
  re-pointed in the next step

Current follow-up for Issue `#13`:
- `RUN_PHASE8B_BASELINE=true` is the dedicated mode for phase8b hardware
  baseline work
- the intended path is
  `build_phase8b -> flash_phase8b_boot_loader -> download_phase8b_app -> provision_phase8b_credentials -> confirm_phase8b_mqtt`
- legacy `aws_demos` / GUI / OTA jobs are intentionally suppressed in this mode
  so scarce hardware time is spent only on the new baseline
