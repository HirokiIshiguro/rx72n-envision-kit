# aws_ether_rx72n_envision_kit

Planned RX72N application project on top of the `iot-reference-rx` Ethernet baseline.

Primary seed:
- `iot-reference-rx/Projects/aws_ether_ck_rx65n_v2/e2studio_ccrx/`

Expected RX72N-specific adaptation areas:
- RXv3 + DPFPU FreeRTOS port assumptions
- RX72N Ethernet PHY and pin configuration
- UART / CLI port selection
- credential storage and littlefs path
- OTA PAL and `r_fwup` integration

Migration guardrail:
- first target is headless AWS / MQTT / OTA baseline
- GUI and SD update reintegration are follow-up work
