# Phase 8b Upstream Baseline

This staging area is seeded from `iot-reference-rx` so the RX72N migration can
start from the same software baseline that already passed CI/CD in Phase 8a.

## Imported from

- Repository: `iot-reference-rx`
- Commit: `c7ee4a0f31b9591d83b4d55823fa41a989005186`
- Note: upstream submodules were materialized at their pinned revisions before
  copying, and nested `.git` / `.gitmodules` files were stripped from the
  imported snapshot

## Imported directories

- `phase8b/Common/`
  - `common_api/`
  - `FreeRTOS_common/`
  - `littlefs_common/`
  - `patches/`
  - `ports/`
- `phase8b/Configuration/`
  - top-level XML/MDF files
  - `samples/`
- `phase8b/Middleware/`
  - `3rdparty/`
  - `AWS/`
  - `FreeRTOS/`
  - `freertos_plus/`
  - `FreeRTOS-Plus-CLI/`
  - `logging/`
  - `network_transport/`
  - `wifi/`
- `phase8b/Test/`
  - common test harness and OTA PAL tests
- `phase8b/Projects/aws_ether_rx72n_envision_kit/`
  - seed copied from `Projects/aws_ether_ck_rx65n_v2/`
- `phase8b/Projects/boot_loader_rx72n_envision_kit/`
  - seed copied from `Projects/boot_loader_ck_rx65n_v2/`

## Important limitations

- The imported `e2studio_ccrx` projects still contain RX65N-oriented metadata,
  file names, and Smart Configurator outputs.
- This change does not wire `phase8b/` into `.gitlab-ci.yml` yet.
- This change does not claim the new projects build on RX72N yet.
- GUI, SD update, and other Envision Kit UX pieces are still outside the new
  baseline and will be reattached later.

## Next porting steps

1. `#8`: Port the boot loader seed to RX72N and recover headless build.
2. `#9`: Port the application seed and recover MQTT baseline.
3. `#10`: Reconnect OTA on the new baseline.
4. `#12`: Reattach GUI / SD update / Envision Kit specific UX.
