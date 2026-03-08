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
- `Middleware/`
- `Projects/`
- `Test/`

Important: this is not just a directory rename. Project contents, middleware
references, and Smart Configurator outputs also change.

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

This is why Phase 8b-1 is primarily a planning and landing-zone issue.
