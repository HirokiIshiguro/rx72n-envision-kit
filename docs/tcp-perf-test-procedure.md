# TCP perf テスト手順 (iperf3 互換、手動運用)

Phase 8b 第3次 段階5-7 B-3 (#62) で整備した、RX72N Envision Kit の
TCP throughput 計測手順。実機 `tcp_send_performance_task` /
`tcp_receive_performance_task` を iperf3 サーバ相手に走らせて接続性 +
throughput を確認する。

CI 統合 (RUN_TCP_PERF_TEST=true) は別 issue (B-3b) で別途、本ドキュメントは
**手動運用前提**。

## HW トポロジ

```
[ PC / VS Code ssh ]
       │
       ▼
[ Raspberry Pi #2 ] ←── iperf3 server
( ef-saffti-001-rpi-002-rx72nek )
       │ Ethernet (LAN 内)
       ▼
[ Raspberry Pi #3 ] ── flash / UART
( ef-saffti-001-rpi-003-rx72nek )
       │ USB
       ▼
[ RX72N Envision Kit (DUT) ]
   - SCI7 / CN6 (UART log + CLI)
   - Ethernet (LAN 同セグメント)
```

- iperf3 server は **RPi#2** で起動
- DUT (RX72N Envision Kit) は **RPi#3** 経由で flash / UART 操作
- RPi#2 と DUT は同じサブネット上、L2 直結 or スイッチ経由

## 事前準備

### 1. RPi#2 に iperf3 を install

```sh
ssh ishiguro@ef-saffti-001-rpi-002-rx72nek
sudo apt update
sudo apt install -y iperf3
iperf3 --version  # 動作確認
```

### 2. RPi#2 のファイアウォール確認

```sh
# 既定 port 5001 を開放 (ufw 有効環境のみ必要)
sudo ufw allow 5001/tcp
sudo ufw status
```

### 3. ネットワーク疎通確認 (DUT IP 取得)

DUT の IP は DHCP 払い出し。MAC ↔ IP 突合は hardware-config repo の
台帳が一次情報源、現場確認は RPi#2 から:

```sh
# DUT が起動しているとき
ip neigh show | grep "<DUT_MAC>"
# 例: 192.168.1.123 dev eth0 lladdr 74:90:50:XX:XX:XX REACHABLE
```

または DUT の COM7 ログに DHCP 取得時の IP 出力あり (起動直後数秒)。

## 計測手順

### A. DUT → iperf3 server (送信側計測)

DUT 内蔵の `tcp_send_performance_task` が iperf3 server に対して連続
送信する。

#### A-1. RPi#2 で iperf3 server 起動 (受信待ち)

```sh
ssh ishiguro@ef-saffti-001-rpi-002-rx72nek
iperf3 -s -p 5001
```

`Server listening on 5001` を確認。

#### A-2. DUT 側で KVStore 設定 + reset

PC から helper script で実行 (RPi#3 にログインして実行する想定):

```sh
ssh ishiguro@ef-saffti-001-rpi-003-rx72nek
cd /path/to/rx72n-envision-kit
python test_scripts/uart_test/setup_tcp_perf.py \
    --device-id rx72n-03 \
    --server-ip <RPi#2_IP> \
    --server-port 5001
```

script は CLI 経由で `conf set tcpperfip` / `conf set tcpperfport` /
`conf commit` / `reset` を実行する。

#### A-3. DUT 起動後の挙動観察

DUT の COM7 (SCI7, 921600bps) ログ:

```
tcp_send_performance_task: server <ip>:<port> (KVStore)
Connecting iperf server: OK.
... (連続送信中、出力なし)
Shutting down connection to iperf server.
```

iperf3 server (RPi#2) 側に接続表示と転送量が出る。

```
[ ID] Interval           Transfer     Bandwidth
[  5]   0.00-1.00   sec  X.XX MBytes  Y.Y Mbits/sec
...
```

### B. iperf3 client → DUT (受信側計測)

DUT 内蔵の `tcp_receive_performance_task` が port 5001 で listen、
iperf3 client が接続してデータ送信する。

#### B-1. DUT 側準備 (送信タスク停止または送信側構成と切替)

`tcp_send_performance_task` と `tcp_receive_performance_task` は両方
常駐するが、**A の構成と B の構成は同時には成立しない**:
- A: 外部 iperf3 サーバが先に起動 → DUT が connect する
- B: DUT (port 5001 listen) → 外部 iperf3 client が connect する

両 task は port 5001 を使うため、A の DUT 送信先 IP が外部 iperf3
サーバを指す状態だと B の listen は無効。B 単体テストは:

```sh
# DUT の tcpperfip を到達不能 IP に設定し、send task を connect 失敗させる
python test_scripts/uart_test/setup_tcp_perf.py \
    --device-id rx72n-03 \
    --server-ip 169.254.0.1 \
    --server-port 5001
# DUT 起動後、send task は "Connecting iperf server: NG." で sleep
# receive task は port 5001 で listen 継続
```

#### B-2. PC / 別マシンから iperf3 client 起動

```sh
iperf3 -c <DUT_IP> -p 5001 -t 30  # 30秒計測
```

DUT COM7 ログ:

```
Connected from iperf client: OK.
... (連続受信中)
Shutting down connection from iperf client.
```

iperf3 client 側に throughput 結果。

## Pass / Fail 基準 (B-3 暫定)

本段階は **接続性 + 連続送受信の確認** が主目的。throughput 数値は
参考値として記録のみ。

| 観点 | Pass 条件 |
|---|---|
| 接続成立 | DUT log に "Connecting iperf server: OK." / "Connected from iperf client: OK." |
| 連続送受信 | iperf3 で 1秒以上の継続送受信 (途中切断なし) |
| Throughput | 数値記録のみ (参考)、本段階で目標値 set なし |
| Shutdown | DUT log に "Shutting down connection ..." |

## 既知制約

- 本テストは iperf 本来の高精度 throughput 計測ではなく、
  「FreeRTOS-Plus-TCP の socket API 経路が機能するか」と「連続的に
  データが流せるか」の確認が主目的
- DUT 側 buffer サイズ (SEND_DATA_UNIT_LENGTH = 4380) は固定、
  iperf 標準の調整パラメータと完全同等ではない
- TLS なし / 平文 TCP のみ
- 受信側 listen port は 5001 hardcode (KVStore 化未対応、別 issue)

## CI 統合への展望 (B-3b)

本段階は手動運用、CI 統合は B-3b で:

- `.gitlab-ci.yml` に `RUN_TCP_PERF_TEST=true` の job を追加
- Pi runner で iperf3 server 起動 (subprocess)
- setup_tcp_perf.py を CI で呼び出し
- iperf3 server log / DUT UART log を artifact 化
- pass/fail は接続成立 + 1秒以上送受信を script で判定
- (任意) throughput 閾値 check で性能リグレッション検出

## 関連

- Issue: #62 (本ドキュメント整備)
- 直前 issue: #61 (KVStore + CLI command 化)
- 親 issue: #48 (段階5 親 tracking)
- helper script: `test_scripts/uart_test/setup_tcp_perf.py`
- DUT firmware: `Projects/.../tcp_perf/tcp_send_performance_task.c` / `tcp_receive_performance_task.c`
