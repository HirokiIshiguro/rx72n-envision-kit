# boot_loader_rx72n_envision_kit

Planned RX72N boot loader project on top of the `iot-reference-rx` boot loader baseline.

Primary seed:
- `iot-reference-rx/Projects/boot_loader_ck_rx65n_v2/e2studio_ccrx/`

Expected RX72N-specific adaptation areas:
- dual-bank memory layout
- boot area ROM budget
- RX72N flash / SCI / pin configuration
- `r_fwup` configuration for RX72N

Important:
- MCUboot migration is not part of this initial step
- first goal is to recover a buildable `r_fwup`-based boot path
