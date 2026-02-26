# はじめに
* 本項は未実装
* 将来更新F/Wにて実現しデモ動作、TLS通信性能ベンチマーク等が可能なようにする
* RX72N Envision KitのF/Wには未実装だが、単体機能としては以下のように完成済

# Trusted Secure IP(TSIP)の概要
* RXファミリは Trusted Secure IP というセキュリティIPを搭載しているモデルがある
* RX72N Envision Kit はそのモデルを採用している
* Trusted Secure IP は平たく言うと暗号回路である
* 暗号回路というと、AES、RSA、SHA、楕円曲線などの暗号アルゴリズムを高速に演算するものを指すことが多い
* Trusted Secure IP はそれだけに留まらず、暗号演算用の鍵データを回路内でガッチリガードする機能を持つ
    * 鍵データを不揮発性メモリに保持する際には、暗号化して回路外に取り出す機構を備えている
* また、Trusted Secure IP は様々な暗号利用モードに対応できるようフレキシブルな設計となっている
    * たとえば、SSL (規格化後の名称はTLS）のような複雑な機構もソフトウェアとの組み合わせにより対応が可能となる
        * TLSの場合、暗号鍵の素となる「プリマスターシークレット」や、鍵交換後の「セッション鍵」を回路内で保持し、決してCPU側からは見えない状態にできる
            * これにより、ソフトウェア不具合がありメモリダンプがチップ外部から実行可能な状態になってしまったとしても、メモリ上には暗号化された「プリマスターシークレット」や「セッション鍵」しか存在せず、システム上安全な状態が保たれる
* プリミティブなメカニズムや性能は以下ページ参照
    * https://github.com/renesas/rx72n-envision-kit/wiki/1-Trusted-Secure-IP%E3%83%89%E3%83%A9%E3%82%A4%E3%83%90#trusted-secure-ip%E3%83%89%E3%83%A9%E3%82%A4%E3%83%90-%E9%8D%B5%E7%AE%A1%E7%90%86%E3%81%AE%E6%A6%82%E5%BF%B5

# Mbed TLSとの連携
- FreeRTOS with IoT Libraries (https://github.com/aws/amazon-freertos) では、Mbed TLS (https://tls.Mbed.org/) というサードパーティ製の暗号通信ライブラリを使用している
    - Mbed TLSは現在Armがライセンスを管理している、SSL/TLSによる暗号通信を実現するオープンソースのライブラリ
    - SSL/TLSは通信の暗号化により盗聴防止・改ざん検知・なりすまし検知を行う技術で、今日のウェブページ等では当たり前に使用されている
    - AWS IoTとの接続にもSSL/TLSを使用する
- Mbed TLSはそのままでも使用可能であるが、暗号処理部分をソフトウェアからTSIPに差し替えることで様々なメリットを享受できる
    - 暗号処理をTSIPのハードウェアアクセラレータで行うため、CPU上でのソフトウェア処理と比較してハンドシェイク時間の短縮と通信速度の大幅な向上が図れる
    - ユーザ鍵をを平文で扱わないため、様々な脅威からユーザ鍵を守ることが可能
- 以上のように、限られたリソースでセキュリティを実現する必要があるIoT製品にTSIPとMbed TLSの連携は適している

## 通信速度の実測値
- いくつかの暗号スイート (SSL/TLSで使用するアルゴリズムのセット) を使用して1MBのデータ転送を行った
    - 1つの暗号スイートに対して、TSIP連携なし/あり、上り/下りの計4パターンで計測
    - 通信インタフェースはEthernetを使用
    - 1MBのデータ転送を5回行い、その平均値を掲載
- 以下の表に示す通り、TSIPを使用しない場合は数Mbps程度の速度であったが、TSIP連携を行うことで20Mbps以上の通信速度を達成した
    - OTAや動画送信といった、大容量データの通信にも使用可能
    - SSL/TLS通信において通信速度を決めるのはブロック暗号処理とハッシュ演算処理の速度であるが、TSIPでは速度低下を気にせず強固なブロック暗号モードおよびハッシュ演算処理を使用することができる
        - 256bit AES-CBCは128bit AES-CBCと比較すると処理の繰り返し回数 (ラウンド数) が多いため、ソフトウェア実装では速度が低下する
        - AES-GCMはAES-CBCと比較して複雑な処理を行うため、ソフトウェア実装では速度が低下する
- この結果は、RX65N@120MHz で計測したものである

|Cipher Suite|Block Cipher|Mbed TLS|Mbed TLS w/ TSIP|
|---|---|---:|---:|
|TLS_RSA_WITH_AES_128_CBC_SHA|128bit AES-CBC|Up: **6.4**Mbps <br> Down: **6.6**Mbps|Up: **25.0**Mbps <br> Down: **28.3**Mbps|
|TLS_RSA_WITH_AES_256_CBC_SHA|256bit AES-CBC|Up: **5.5**Mbps <br> Down: **5.6**Mbps|Up: **24.2**Mbps <br> Down: **27.2**Mbps|
|TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256|128bit AES-GCM|Up: **3.7**Mbps <br> Down: **3.8**Mbps|Up: **22.4**Mbps <br> Down: **29.5**Mbps|

<!--
以下はクライアント側が対応しているCipher Suites

|Cipher Suite|Mbed TLS|Mbed TLS w/ TSIP|
|---|---:|---:|
|TLS_RSA_WITH_AES_128_CBC_SHA|Up: Mbps <br> Down: Mbps|Up: Mbps <br> Down: Mbps|
|TLS_RSA_WITH_AES_256_CBC_SHA|Up: Mbps <br> Down: Mbps|Up: Mbps <br> Down: Mbps|
|TLS_RSA_WITH_AES_128_CBC_SHA256|Up: Mbps <br> Down: Mbps|Up: Mbps <br> Down: Mbps|
|TLS_RSA_WITH_AES_256_CBC_SHA256|Up: Mbps <br> Down: Mbps|Up: Mbps <br> Down: Mbps|
|TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256|Up: Mbps <br> Down: Mbps|Up: Mbps <br> Down: Mbps|
|TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256|Up: Mbps <br> Down: Mbps|Up: Mbps <br> Down: Mbps|
|TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256|Up: Mbps <br> Down: Mbps|Up: **21.8**Mbps <br> Down: **28.8**Mbps|
|TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256|Up: Mbps <br> Down: Mbps|Up: **22.4**Mbps <br> Down: **29.5**Mbps|
-->

## 実装方法
* Mbed TLSへのTSIPの実装方法を記したアプリケーションノートを準備完了しました。
  * https://www.renesas.com/software-tool/trusted-secure-ip-driver
    * RXファミリ用 Trusted Secure IPドライバ（バイナリ版）V1.12以降に解説書が同梱されています
      * \r20an0548jj0112-lib-rx-tsip-security\reference_documents\ja
        * r01an5880jj0100-rx-tsip.pdf
          * RXファミリ TSIPドライバを用いたTLS実装方法