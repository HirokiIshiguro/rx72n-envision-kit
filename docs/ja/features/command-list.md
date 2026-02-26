# はじめに
* ベンチマークデモにはコマンド・レスポンス機能が実装されている
* 内部状態をモニタしたり、設定情報を書き込んだりするコマンドが実装されている

# コマンド・レスポンス実行方法
* 以下ページの シリアルターミナルデモ 参照
    * [初期ファームウェア動作確認方法](../../quick-start/confirm-factory-image-behavior.md)

# コマンドリスト

|対応バージョン|コマンド|引数|機能|
|-----|-----|-----|-----|
|v0.9.3|version||バージョンデータを読み出す|
|v0.9.3|freertos|cpuload read|FreeRTOSが保持するCPU負荷率情報を読み出す|
|v0.9.3|freertos|cpuload reset|FreeRTOSが保持するCPU負荷率情報をリセットする|
|v1.0.1|timezone|\<timezone\>|タイムゾーンを設定する。<timezone>書式は [link](https://github.com/renesas/rx72n-envision-kit/blob/88695141fc1586bd49b38700bbd6837631175939/vendors/renesas/boards/rx72n-envision-kit/aws_demos/src/smc_gen/r_sys_time_rx/r_sys_time_rx_if.h#L46) 参照。UTC+09:00 と入力すれば日本標準時。|
|v1.0.2|reset||ソフトウェアリセットを発行する|
|v1.0.2|dataflash|info|データフラッシュの一般情報(総容量、空き領域等)を読み出す|
|v1.0.2|dataflash|read|データフラッシュに書き込まれている設定情報をすべてを読み出す|
|v1.0.2|dataflash|write aws clientprivatekey|AWS接続のためのクライアント秘密鍵(PEM方式)を書き込む。コマンド実行後入力待ちとなる。exitかquitで強制的に入力状態をキャンセル可能|
|v1.0.2|dataflash|write aws clientcertificate|AWS接続のためのクライアント証明書(PEM方式)を書き込む。コマンド実行後入力待ちとなる。exitかquitで強制的に入力状態をキャンセル可能|
|v1.0.2|dataflash|write aws codesignercertificate|Amazon FreeRTOS OTA実行時に使用するファームウェア検証用公開鍵の証明書(PEM方式)を書き込む。コマンド実行後入力待ちとなる。exitかquitで強制的に入力状態をキャンセル可能|
|v1.0.2|dataflash|write aws mqttbrokerendpoint <mqtt_broker_end_point>|AWS接続のためのMQTTブローカーエンドポイントを書き込む|
|v1.0.2|dataflash|write aws iotthingname <iot_thing_name>|AWS接続のためのIOT Thing Nameを書き込む|
|v1.0.3|dataflash|erase|データフラッシュに保存された設定情報をすべて消去する|
|v1.0.4|dataflash|write tcpsendperformanceserveripaddress <ip_address>|TCP送信性能測定サーバのIPアドレスを登録する。<ip_address>の例：192.168.1.206|
|v1.0.4|dataflash|write tcpsendperformanceserverportnumber <port_number>|TCP送信性能測定サーバのポート番号を登録する。<port_number>の例：5001|
|v2.0.0|dataflash|write tracealyzerserveripaddress <ip_address>|TracealyzerサーバのIPアドレスを登録する。<ip_address>の例：192.168.1.206|
|v2.0.0|dataflash|write tracealyzerserverportnumber <port_number>|Tracealyzerサーバのポート番号を登録する。<port_number>の例：12000|
