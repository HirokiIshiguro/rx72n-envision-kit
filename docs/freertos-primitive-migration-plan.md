# FreeRTOS Primitive Migration Plan

## Status

This is the active migration plan as of 2026-04-05.

Historical `phase8b/` work is preserved only as reference and is no longer the
active execution path.

## Active Baseline

- Start point: `master` at `dd1a48924ec7ab44d5f59c797a0f0bfc01e31fbe`
- Reference source: `iot-reference-rx` `v202406.01-LTS-rx-1.1.1`
- Current runtime acceptance gate: MQTT only
- Current boot path: keep the user-authored RX72N boot loader
- Explicitly out of scope for the initial migration: `r_fwup`
- Final long-term goal: MCUboot, after the MQTT baseline is stable

## Hard Rules

1. Every migration step starts from `master`, not from historical `phase8b/`
   branches.
2. Each primitive gets its own issue, branch, and MR.
3. Do not combine boot loader replacement, middleware replacement, app
   rewiring, and layout migration in one MR.
4. Until the MQTT baseline is stable, OTA, Fleet Provisioning, GUI, and final
   layout migration are deferred.
5. `r_fwup`, `phase8b/`, and FWUP v2 RSU tooling are not part of the active
   forward path.

## Superseded Assumptions

The following older assumptions are now obsolete:

- `phase8b/` staging root is the main migration path
- `r_fwup`-based RX72N port is the migration target
- phase8b-specific CI jobs are the mainline validation path
- OTA must be revalidated before the MQTT baseline is declared usable

## Acceptance Gates

### Build Gate

- `projects/renesas/rx72n_envision_kit/e2studio/boot_loader` builds headless
- `projects/renesas/rx72n_envision_kit/e2studio/aws_demos` builds headless

### Runtime Gate

- RX72N boots over Ethernet
- AWS IoT MQTT connect succeeds
- Publish succeeds
- Subscribe receive succeeds

### Deferred Gates

- OTA end-to-end execution
- Fleet Provisioning execution
- GUI / SD update reintegration
- Top-level layout migration to `Common/Configuration/Demos/Middleware/Projects/Test`
- MCUboot adoption

## Primitive Queue

| Order | Primitive | Suggested issue title | Suggested branch name | Suggested MR title | Scope | Done when |
|------:|-----------|-----------------------|-----------------------|--------------------|-------|-----------|
| 1 | Contract reset | `Reset FreeRTOS migration contract to master + primitive steps` | `codex/<issue-id>-migration-contract-reset` | `docs: reset FreeRTOS migration contract to master baseline` | Replace the active migration plan, mark `phase8b` / `r_fwup` strategy as historical, define MQTT-only runtime gate | Active docs point to this plan, and old `phase8b` plan is clearly marked as superseded |
| 2 | Boot loader contract freeze | `Freeze custom RX72N boot loader contract before middleware migration` | `codex/<issue-id>-freeze-custom-bootloader-contract` | `docs: freeze custom RX72N boot loader contract` | Document the user-authored boot loader ABI: image format, signature expectations, bank behavior, metadata, UART/download expectations | Boot loader interfaces are fixed enough that later MRs can target them without redesign |
| 3 | Kernel-only alignment | `Align FreeRTOS Kernel baseline with iot-reference-rx v202406.01-LTS-rx-1.1.1` | `codex/<issue-id>-align-freertos-kernel` | `freertos: align kernel baseline with iot-reference-rx` | Audit and update `freertos_kernel/` only; keep project/app behavior unchanged | Both projects still headless-build, and kernel delta is isolated to `freertos_kernel/` plus minimal config fallout |
| 4 | TCP/IP-only alignment | `Align FreeRTOS-Plus-TCP baseline and RX72N network interface` | `codex/<issue-id>-align-freertos-plus-tcp` | `net: align FreeRTOS-Plus-TCP and RX72N NIC path` | Update `libraries/freertos_plus/standard/freertos_plus_tcp/` and the RX72N Ethernet glue only | Headless build passes and Ethernet init path remains intact enough for later MQTT work |
| 5 | MQTT-path library alignment | `Align MQTT-path libraries with iot-reference-rx baseline` | `codex/<issue-id>-align-mqtt-path-libs` | `middleware: align MQTT-path libraries with reference baseline` | Update the libraries required to reach MQTT: `coreMQTT`, `coreMQTT-Agent`, `coreJSON`, `coreHTTP`, `coreSNTP`, `logging`, `backoffAlgorithm`, and directly coupled config | Headless build passes and library changes stay out of boot loader / OTA redesign |
| 6 | Crypto and storage alignment | `Align crypto and credential-storage libraries for MQTT baseline` | `codex/<issue-id>-align-crypto-storage` | `security: align crypto and credential storage for MQTT baseline` | Update `mbedtls`, PKCS11-related code, and littlefs/credential storage pieces needed for MQTT auth | AWS credential load and TLS dependencies build cleanly without introducing `r_fwup` |
| 7 | Minimal app path rewrite | `Reduce aws_demos to the minimum Ethernet + MQTT execution path` | `codex/<issue-id>-reduce-aws-demos-to-mqtt-baseline` | `app: reduce aws_demos to Ethernet plus MQTT baseline` | Rewire `aws_demos` so the first supported runtime target is only Ethernet + MQTT connect/pub/sub | Both projects build and the app path is no longer blocked by OTA, GUI, or Fleet Provisioning dependencies |
| 8 | MQTT runtime validation | `Validate MQTT baseline on hardware` | `codex/<issue-id>-validate-mqtt-baseline` | `test: validate MQTT baseline on RX72N hardware` | Run the agreed runtime gate on hardware and fix only blockers for MQTT connectivity | Connect, publish, and subscribe pass on hardware |
| 9 | Post-MQTT backlog split | `Split post-MQTT work into Fleet Provisioning / OTA / layout / MCUboot tracks` | `codex/<issue-id>-split-post-mqtt-backlog` | `docs: split post-MQTT migration backlog` | After MQTT is stable, create the next issue queue for Fleet Provisioning, OTA, final layout migration, and MCUboot | Post-MQTT work is explicitly split and no longer coupled to the MQTT baseline branch set |

## Recommended Execution Order

1. Finish primitives 1 and 2 before changing middleware payloads.
2. Finish primitives 3 to 6 with build-only validation.
3. Finish primitive 7 and then run primitive 8 as the first runtime checkpoint.
4. Only after primitive 8 passes, open primitive 9 and fan out to Fleet
   Provisioning, OTA, final layout migration, and MCUboot.

## Notes

- The current repository already contains FreeRTOS Kernel `11.1.0`, so the
  kernel step is expected to be an audit-and-alignment task, not a blind
  version jump.
- The legacy `aws_demos` application still contains firmware-update-era code,
  GUI coupling, and board-specific utility logic. The app rewrite step must
  remove those dependencies from the MQTT critical path instead of trying to
  modernize everything at once.
- Historical `phase8b` artifacts may still be useful as reference, but they are
  not acceptance targets and should not be used as merge bases.
