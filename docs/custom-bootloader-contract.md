# Custom RX72N Boot Loader Contract

## Status

This document freezes the contract of the current user-authored RX72N boot
loader before the FreeRTOS middleware migration proceeds further.

It describes the boot path that is valid today on `master`. It is not a design
proposal for MCUboot.

## Source Of Truth

Runtime behavior and on-flash data layout are defined by these files:

- `projects/renesas/rx72n_envision_kit/e2studio/boot_loader/src/rx72n_boot_loader.c`
- `projects/renesas/rx72n_envision_kit/e2studio/boot_loader/src/smc_gen/r_config/r_bsp_config.h`
- `vendors/renesas/boards/rx72n-envision-kit/aws_demos/application_code/renesas_code/utility/firm_update.c`
- `tools/ci/download_aws_demos.py`
- `tools/runner-handle/runner_handle/uart_download.py`
- `test_scripts/uart_test/test_uart_download.py`
- `test_scripts/uart_test/test_boot_loader.py`
- `test_scripts/uart_test/provision_aws.py`
- `test_scripts/uart_test/test_ota.py`

If later work changes the behavior described here, that change must update this
document in the same MR.

## Contract Summary

- The forward boot path is the existing custom RX72N boot loader.
- `r_fwup` is not part of this boot path.
- `phase8b` RELFWV2 images are not part of this boot path.
- The accepted update package format is the legacy `Renesas` RSU format.
- The first runtime acceptance target for the migration remains MQTT only, but
  the boot path itself must stay compatible with the existing RSU-based update
  flow until a later dedicated replacement step.
- MCUboot is a future replacement project, not a current dependency.

## Hardware And UART Contract

The current boot loader project is configured for:

- RX72N dual-bank device configuration
- `SCI7`
- `921600` bps
- interrupt priority `15`

Those values come from
`projects/renesas/rx72n_envision_kit/e2studio/boot_loader/src/smc_gen/r_config/r_bsp_config.h`.

The CI and local automation currently assume the same UART path:

- log / download port: `COM7`
- baud rate: `921600`
- boot banner contains: `RX72N secure boot program`
- ready banner: `send "userprog.rsu" via UART.`
- success marker after handoff: `jump to user program`

The command/UART provisioning channel used by the application is separate from
this boot loader UART path.

## Flash Ownership Contract

The custom boot loader owns bank selection and swap by directly calling:

- `R_FLASH_Control( FLASH_CMD_BANK_TOGGLE, NULL )`
- software reset through `SYSTEM.SWRR = 0xa501`

This means:

- bank swap semantics are defined by the boot loader itself
- there is no `r_fwup` control block or `r_fwup` state machine in the forward path
- later migration work must not silently replace this contract with another boot
  scheme

The boot loader code defines three major flash regions symbolically:

- execute area: `FLASH_CF_HI_BANK_LO_ADDR`
- temporary/update area: `FLASH_CF_LO_BANK_LO_ADDR`
- boot loader mirror area in the opposite bank:
  `FLASH_CF_BLOCK_83` upward with the configured small/medium block counts

Data flash used by the application payload is written separately, starting at
`FLASH_DF_BLOCK_32`.

## Lifecycle Contract

The current boot loader recognizes these image lifecycle values:

- `0xFF`: `LIFECYCLE_STATE_BLANK`
- `0xFE`: `LIFECYCLE_STATE_TESTING`
- `0xFC`: `LIFECYCLE_STATE_INITIAL_FIRM_INSTALLED`
- `0xF8`: `LIFECYCLE_STATE_VALID`
- `0xF0`: `LIFECYCLE_STATE_INVALID`

Behavior that later work must preserve unless explicitly changed:

1. On boot, the boot loader inspects the control block in both banks.
2. If bank1 is `TESTING`, it verifies the staged image.
3. If verification succeeds, bank1 is rewritten as `VALID` and a bank swap +
   software reset is triggered.
4. If verification fails, bank1 is rewritten as `INVALID` and the system does
   not promote the image.
5. If bank0 is `VALID`, the boot loader may erase stale staged contents in bank1
   before jumping to the user program.
6. If bank0 is blank, the boot loader enters install/recovery behavior instead
   of jumping to the application.

## Update Package Contract

The accepted update stream is the legacy RSU format whose leading bytes start
with `Renesas`.

Current tooling expectations:

- filename convention: `userprog.rsu`
- CI generation path: `tools/mcu-tool-rx/mot_to_rsu.py`
- UART download tools send the raw RSU file without higher-level framing

The current boot loader code understands two integrity scheme strings:

- `hash-sha256`
- `sig-sha256-ecdsa`

The migration should treat `sig-sha256-ecdsa` as the required real path,
because the current CI and OTA-related tooling generate signed ECDSA images.

`RELFWV2` is not a supported magic for this boot path.

## On-Flash Control Block Contract

The boot loader and the application-side staging code share the same
`FIRMWARE_UPDATE_CONTROL_BLOCK` layout.

The layout is:

| Offset | Size | Field | Meaning |
|-------:|-----:|-------|---------|
| `0x000` | 7 | `magic_code` | Legacy RSU magic, currently `Renesas` |
| `0x007` | 1 | `image_flag` | Lifecycle state |
| `0x008` | 32 | `signature_type` | Integrity scheme string |
| `0x028` | 4 | `signature_size` | Signature byte count |
| `0x02C` | 256 | `signature` | Raw ECDSA `r||s` bytes in current signed path |
| `0x12C` | 4 | `dataflash_flag` | Data flash presence flag |
| `0x130` | 4 | `dataflash_start_address` | Data flash payload start |
| `0x134` | 4 | `dataflash_end_address` | Data flash payload end |
| `0x200` | 4 | `sequence_number` | Monotonic image sequence metadata |
| `0x204` | 4 | `start_address` | Code image start address |
| `0x208` | 4 | `end_address` | Code image end address |
| `0x20C` | 4 | `execution_address` | Reset/jump execution address metadata |
| `0x210` | 4 | `hardware_id` | Hardware identity metadata |

The first `0x200` bytes act as the signed-image header prefix. The descriptor
fields start at `0x200`.

For the legacy OTA helper, the RSU file is interpreted as:

- `0x000-0x1FF`: header
- `0x200-0x2FF`: descriptor
- `0x300-...`: code payload
- trailing data flash payload at the end of the full legacy RSU

Any new generator or parser introduced during migration must preserve this
layout unless the boot loader contract is deliberately revised.

## Verification Contract

The boot loader verifies the image using SHA-256 over the payload area after the
first `0x200` bytes.

For the current signed path:

- public key format: PEM
- signature scheme: ECDSA P-256 over SHA-256
- verification library: `tinycrypt` + `uECC_verify`
- boot loader expects raw `r||s` bytes in the control block signature field

The boot loader loads the code signer public key from secure data flash using
the object label:

- `code signer public key`

If that object does not exist yet, the boot loader provisions the built-in
default public key from `code_signer_public_key.h`.

This is a separate contract from the application CLI command
`dataflash write aws codesignercertificate`, which belongs to the application
credential/OTA flow rather than the boot loader UART protocol itself.

## Install And Recovery Contract

The current boot loader has two operational modes:

- install / recovery mode when no valid executable image is available
- validation / handoff mode when a valid image already exists

Install mode behavior that automation depends on:

1. Boot banner is printed.
2. The secure boot mirror may be copied to the opposite bank.
3. Install areas are erased.
4. The boot loader prints `send "userprog.rsu" via UART.`
5. Code flash payload is received in `32KB` chunks over UART with double
   buffering.
6. Progress messages are printed during code-flash and data-flash installation.
7. Signature verification runs before reset.
8. A software reset occurs after install completion.

Validation / handoff behavior that automation depends on:

1. The boot loader re-checks the executable bank after reset.
2. It may erase stale staged contents.
3. It prints `jump to user program` immediately before handing off to the app.

## CI And Tooling Contract

The following tooling assumptions are now frozen for the current boot path:

- `.mot` to legacy `.rsu` conversion uses `mot_to_rsu.py`
- UART download waits for `send "userprog.rsu" via UART.`
- UART download success is confirmed by `jump to user program`
- boot loader reset for CI is typically triggered through `rfp-cli ... -run`
- local and CI scripts may inspect progress strings such as:
  - `installing firmware`
  - `completed installing firmware`
  - `integrity check`
  - `installing const data`
  - `completed installing const data`
  - `software reset`

Any change to these user-visible strings is a tooling contract change.

## Explicit Non-Goals

This document does not freeze:

- the final OTA protocol for the post-MQTT migration
- Fleet Provisioning behavior
- GUI / SD update UX details outside of the RSU filename convention
- the final `Common/Configuration/Demos/Middleware/Projects/Test` repository layout
- the future MCUboot design

## Temporary Areas Reserved For Future MCUboot Work

The following are intentionally temporary and may change only in a dedicated
MCUboot track:

- legacy `Renesas` RSU packaging
- the custom lifecycle state values above
- direct bank toggle from the custom boot loader
- the secure boot mirror copy scheme
- the exact control-block layout and reserved fields

Until that dedicated replacement work starts, later middleware migration MRs
must treat this boot loader contract as fixed input.
