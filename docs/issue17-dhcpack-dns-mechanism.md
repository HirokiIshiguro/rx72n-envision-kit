# Issue #17 Follow-up

`Issue #16` / `MR !48` で入れた `9224a597` により、
dataflash MAC と RX hardware MAC の不一致が解消され、
`#1/#2/#3` の `confirm_aws_mqtt` は回復した。

一方で、pre-fix 状態でも mirror-port 上では unicast の `DHCPOFFER` / `DHCPACK`
が観測されており、

- DHCP は進んでいた
- DNS reply は失敗していた

という差分の mechanism はまだ完全には説明できていない。

この issue では current MR の merge を優先し、
以下を controlled experiment として後追いで解明する。

1. `9224a597` を一時的に戻した build を `#01` 単独で再現する。
2. 正しい mirror-port 配線で `DHCPACK` / `DNS reply` / raw UART を同時観測する。
3. DHCP socket / DNS socket / RX driver filter / broadcast flag の差分を詰める。
4. 必要なら FreeRTOS+TCP または Renesas Ethernet driver 側の受信経路を追加調査する。

## Resume Procedure (2026-03-14)

`pipeline #784` / merged `MR !48` の 3-set legacy baseline を土台に、
current `master` 上で controlled experiment を再開する。

- `RUN_ONLY_DEVICE_SLOT=01`
- `RUN_AWS_TESTS=true`
- `RUN_SD_UPDATE_TEST=false`
- `RUN_OTA_TEST=false`
- `RUN_HW_HEALTHCHECK=false`
- `RUN_ISSUE17_PRE_HW_MAC_REPRO=true`
- `ISSUE17_RECORD_MQTT_EVIDENCE=true`

この組み合わせで、

- `9224a597` を build 時だけ一時的に戻した aws_demos
- `#01` 単独の flash -> provision -> MQTT
- raw UART transcript
- mirror-port packet capture (`issue17_mqtt_*.packet.*`)

を同じ pipeline artifacts に残せる。
