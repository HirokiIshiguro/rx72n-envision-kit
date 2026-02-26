# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 3 本 
    * LANケーブル(インターネット接続可能なネットワークに接続されていること) × 1 本
    * [USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/) × 1 台
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2020-04](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
                * 初回起動時に時間がかかることがある
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.01以降
            * [Tera Term](https://osdn.net/projects/ttssh2/) 4.105で動作確認済み
                * [シリアル接続における高速なファイル転送](https://teratermproject.github.io/manual/5/ja/setup/teraterm-trans.html#FileSendHighSpeedMode) の FileSendHighSpeedMode を OFF にする
                    * Tera Term -> 設定 -> 設定の読み込み -> TERATERM.INI を テキストエディタで開く -> 設定を変更 -> 保存 -> Tera Term再起動

# 前提条件
* FreeRTOSチュートリアル [デバイスをAWS IoTに登録する](https://github.com/renesas/amazon-freertos/wiki/%E3%83%87%E3%83%90%E3%82%A4%E3%82%B9%E3%82%92AWS-IoT%E3%81%AB%E7%99%BB%E9%8C%B2%E3%81%99%E3%82%8B) を完了すること
    * 自分のAWSアカウントのIoTエンドポイントの文字列が入手出来ていること
        * 例: a164xxxxxxxxxx-ats.iot.ap-northeast-1.amazonaws.com
    * 自分のRX72N Envision Kit用の「モノの名前」の文字列が入手出来ていること
        * 例: rx72n_envision_kit
    * 自分のRX72N Envision Kit用の「モノ」がAWSにアクセスするための証明書/パブリックキー/プライベートキーのファイルが入手出来ていること
* [FreeRTOS 無線による更新](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/freertos-ota-dev.html) の各前提条件を完了すること
    * ここでは各項目における実際の操作について2020/06/14時点の注意事項を中心に紹介する

# キーワード
* [FreeRTOS 無線による更新](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/freertos-ota-dev.html) では以下キーワードが出てくる
* キーワードに対し入力が求められる名前や、予めアカウント毎に決まっている値がある
* テキストエディタにキーワードを張り付けておき、手順を進める毎にその名前や値を列挙しておくとよい
* 特にアクセスポリシー用のコードには、これらキーワードを代名詞とした状態で解説されており、ポリシー適用前に自力でコード書き換えが必要である
* 本稿ではキーワードに対し以下のように名前や値を定義する
* 各項で名前入力が求められた場合、ここで定義する名前を入力するとよい
```
AWSアカウントID: 211xxxxxxxxx (x=伏字)
IAMユーザ: rx72n-envision-kit
S3バケット: rx72n-envision-kit
OTAサービスロール: rx72n-envision-kit-ota
OTAサービスロースIAMアクセスポリシー: rx72n-envision-kit-ota-iam
OTAサービスロースS3バケットアクセスポリシー: rx72n-envision-kit-ota-s3
OTAユーザーポリシー: rx72n-envision-kit-ota-user-policy
IAMユーザコード署名オペレーションアクセスポリシー：rx72n-envision-kit-iam-code-signer
```

# AWSアカウントIDの調べ方
* [IAMコンソール](https://console.aws.amazon.com/iam/home) にて画面左下に表示されている数列がAWSアカウントID

# [FreeRTOS 無線による更新](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/freertos-ota-dev.html) の各前提条件
* [更新を保存する Amazon S3 バケットを作成する](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/dg-ota-bucket.html)
    * 5.「[Next (次へ)] を選択して、デフォルトのアクセス許可を受け入れます。」については特に設定項目なし
* [OTA 更新サービスロールを作成する](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/create-service-role.html)
    * 7.「[Next: Tags (次の手順: タグ)] を選択します。」の前に「[Next: Access Control (次の手順: アクセス制限)] 」が必要なようだがここでは何も設定しなくてよい
* [OTA ユーザーポリシーの作成](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/create-ota-user-policy.html)
    * 予めIAMユーザを登録しておく必要がある
        * [IAMコンソール](https://console.aws.amazon.com/iam/home) にて「ユーザ」を選択し「ユーザを追加」ボタンを押す
        * IAMユーザ名は rx72n-envision-kit とする
        * アクセスの種類で「プログラムによるアクセス」を選んでおく
        * 他はデフォルトでOK
        * あとは [OTA ユーザーポリシーの作成](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/create-ota-user-policy.html) に従って進めていく
* [コード署名証明書の作成](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/ota-code-sign-cert.html)
    * ルネサスはRX65NにてOTA込みの認証を取得中であり、まだAWS公式に紹介記事やAWS上の設定項目に現れない
    * [カスタムハードウェアのコード署名証明書の作成](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/ota-code-sign-cert-other.html) の項目に従って署名証明書の作成とAWS Certificate Managerへの登録を実施する
        * [署名証明書の作成](https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8#openssl%E3%81%A7%E3%81%AEecdsasha256%E7%94%A8%E3%81%AE%E9%8D%B5%E3%83%9A%E3%82%A2%E7%94%9F%E6%88%90%E6%96%B9%E6%B3%95)
            * RX72N Envision Kit用に作成済のサンプルを用意した: [link](https://github.com/renesas/rx72n-envision-kit/tree/master/sample_keys)
        * [カスタムハードウェアのコード署名証明書の作成](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/ota-code-sign-cert-other.html) では AWS Certificate Manager へ証明書の登録方法としてコマンドラインが紹介されているが、AWS IoT Coreの画面上からもインポート可能なため、ここでは何もしなくてよい
            * 参考: [AWS Certificate Manager](https://ap-northeast-1.console.aws.amazon.com/acm/home?region=ap-northeast-1) 
* [Code Signing for AWS IoT へのアクセスの許可](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/code-sign-policy.html)
    * 特筆事項無し
* [OTA ライブラリで FreeRTOS をダウンロードする](https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/ota-download-freertos.html)
    * 以降はAWS認証済みの環境での話であり、RX72N Envision KitはAWS認証未取得のため、以下手順で進む

# OTAによるファームアップデート手順
* ルネサスの Amazon FreeRTOS wikiのOTA解説ページの[実機動作確認方法](https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8#%E5%AE%9F%E6%A9%9F%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95) の「手順まとめ」を参照
    * 注意事項
        * RX65N RSK は RX72N Envision Kit、RX65NはRX72Nに読み替える
        * user_application は aws_demos に読み替える
        * 手順5のブートローダ用公開鍵はRX72N Envision Kitではすでにソースコードに埋め込み済み
        * 手順3の各種パラメータおよび、手順6のアプリケーション用公開鍵はRX72N Envision KitではUART経由で入力必要
        * UART経由で入力した各種パラメータはデータフラッシュに保持され、RX72N Envision Kitの電源がOFFになっても消えることはない
        * また、ファームウェアアップデートしても前の状態が維持されるため、コンパイルする毎に調整する必要がない
* 各種パラメータ入力はCN8のUSBコネクタから実施可能
* 動作確認時はOTAの進行状況(Amazon FreeRTOSのログ)はCN6(PMOD)のUSBコネクタから出力される
    *  [USB-シリアル変換 PMODモジュール](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/) を接続し、Tera Termでモニタするとよい
        * CN6やCN8の接続方法やTera Term設定は以下参照
            * [ベンチマークデモ起動](https://github.com/renesas/rx72n-envision-kit/wiki/%E5%88%9D%E6%9C%9F%E3%83%95%E3%82%A1%E3%83%BC%E3%83%A0%E3%82%A6%E3%82%A7%E3%82%A2%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95#%E3%83%99%E3%83%B3%E3%83%81%E3%83%9E%E3%83%BC%E3%82%AF%E3%83%87%E3%83%A2%E8%B5%B7%E5%8B%95)

# 手順3の各種パラメータおよび、手順6のアプリケーション用公開鍵入力方法
* ルネサスの Amazon FreeRTOS wikiのOTA解説ページの[実機動作確認方法](https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8#%E5%AE%9F%E6%A9%9F%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95) の「手順まとめ」の手順19まで進める（手順3と手順6のソースコード書き換えは無視）
* Tera Term で CN8と通信できることを確認 (デフォルト状態だとブートローダのログの後に「RX72N Envision Kit」とプロンプトが出て入力状態となる)
## クライアント秘密鍵の入力
* dataflash write aws clientprivatekeyと入力し、エンターキー
* 入力待ちとなる
* クライアント秘密鍵を入力: AWS IoT Core が生成したクライアント秘密鍵（3axxxxxxxx-private.pem.key）をテキストエディタで開きTera Termにコピー&ペースト
  * 注意: 改行コードは "LF" のみである
* stored data into dataflash correctly. と表示されればOK
```
$ RX72N Envision Kit
$ dataflash write aws clientprivatekey
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAzhY82YODydQYFH/yFZONXFYMNJ86US+Ph+snfsinjFFU3kOp
 :
 : (省略)
 :
5M9Nxhh8FDzNJibzbLSZQHJNgEu9nufrOkLLxv/84heYH/W/Ako=
-----END RSA PRIVATE KEY-----
stored data into dataflash correctly.
```
## クライアント証明書の入力
* dataflash write aws clientcertificateと入力し、エンターキー
* 入力待ちとなる
* クライアント証明書を入力: AWS IoT Core が生成したクライアント証明書（3axxxxxxxx-certificate.pem.crt）をテキストエディタで開きTera Termにコピー&ペースト
  * 注意: 改行コードは "LF" のみである
* stored data into dataflash correctly. と表示されればOK
```
RX72N Envision Kit
$ dataflash write aws clientcertificate
-----BEGIN CERTIFICATE-----
MIIDWTCCAkGgAwIBAgIUWNAUkpzF4GO909IxarCG1nLaXO8wDQYJKoZIhvcNAQEL
 :
 : (省略)
 :
UB2bnt0RxcqXtoihQ2KgWWWW699CWKt4EyPoCgxuQ04P4pzlmF60BbESpUfm
-----END CERTIFICATE-----
stored data into dataflash correctly.
```
## コード検証用公開鍵の証明書の入力
* dataflash write aws codesignercertificateと入力し、エンターキー
* 入力待ちとなる
* コード検証用公開鍵の証明書を入力: RX72N Envision Kitのサンプル鍵束にある（secp256r1.crt）をテキストエディタで開きTera Termにコピー&ペースト
  * 注意: 改行コードは "LF" のみである
* stored data into dataflash correctly. と表示されればOK
```
$ dataflash write aws codesignercertificate
-----BEGIN CERTIFICATE-----
MIICYDCCAgYCCQDqyS1m4rjviTAKBggqhkjOPQQDAjCBtzELMAkGA1UEBhMCSlAx
 :
 : (省略)
 :
gQIhAO75WVGyGt58QCGNx3wMcbaDgJ4Xpqj0SWTWdxdz0jh1
-----END CERTIFICATE-----
stored data into dataflash correctly.
```
## IoTエンドポイントの入力
* dataflash write aws mqttbrokerendpoint <mqtt_broker_endpoint> と入力し、エンターキー
* <mqtt_broker_endpoint> は以下で確認可能
    * [AWS IoTのエンドポイントを確認する](https://github.com/renesas/amazon-freertos/wiki/%E3%83%87%E3%83%90%E3%82%A4%E3%82%B9%E3%82%92AWS-IoT%E3%81%AB%E7%99%BB%E9%8C%B2%E3%81%99%E3%82%8B#aws-iot%E3%81%AE%E3%82%A8%E3%83%B3%E3%83%89%E3%83%9D%E3%82%A4%E3%83%B3%E3%83%88%E3%82%92%E7%A2%BA%E8%AA%8D%E3%81%99%E3%82%8B)
* stored data into dataflash correctly. と表示されればOK
```
$ dataflash write aws mqttbrokerendpoint a25xxxxxxxxxxxx-ats.iot.ap-northeast-1.amazonaws.com
stored data into dataflash correctly.
```
## 「モノ」の名前の入力
* dataflash write aws iotthingname <iot_thing_name> と入力し、エンターキー
* <iot_thing_name> は以下で作成した「モノ」の名前
    * [デバイス(モノ)をAWS IoTに登録する](https://github.com/renesas/amazon-freertos/wiki/%E3%83%87%E3%83%90%E3%82%A4%E3%82%B9%E3%82%92AWS-IoT%E3%81%AB%E7%99%BB%E9%8C%B2%E3%81%99%E3%82%8B#%E3%83%87%E3%83%90%E3%82%A4%E3%82%B9%E3%83%A2%E3%83%8E%E3%82%92aws-iot%E3%81%AB%E7%99%BB%E9%8C%B2%E3%81%99%E3%82%8B)
* stored data into dataflash correctly. と表示されればOK
```
$ dataflash write aws iotthingname rx72n_envision_kit
stored data into dataflash correctly.
```
## 正しく各パラメータが書き込めているか確認する
* dataflash read コマンドで書き込み済みのパラメータを全表示する
```
$ dataflash read
label = timezone
data = UTC
data_length(includes string terminator 1byte zero) = 4

label = client_private_key
data = -----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAzhY82YODydQYFH/yFZONXFYMNJ86US+Ph+snfsinjFFU3kOp
QlfU4WyV+Hz15qsHbxEIv/BS4NvgKZdFpfysLdoWJDPKgOqjbJ8Z//5DZP9SRzVi
CQhKO8bAP2XonB8Vx0JfpzHHwKfPspI/1xbCb1ritjboTn4vmZ1jdQE+h8MFhKJQ
 :(以下略)
```

## データフラッシュに保持したパラメータが異常になった場合は以下コマンドで全削除可能
```
$ dataflash erase
completed erasing all flash.
```

# 注意事項
* データフラッシュに保持されている「クライアント証明書」「クライアント秘密鍵」は、ユーザ認証における「ID」「パスワード」に相当する
* 本システムにおいては「クライアント証明書」「クライアント秘密鍵」が平文のままデータフラッシュに配置されており、dataflash readコマンドで容易く外部から読み出せてしまう
* アタッカがこれを悪用すると、当該AWSアカウントに不正ログインされ、大量に通信が発生した場合、当該AWSアカウントに大量の課金請求が届く可能性がある
* 従ってデモセット等に組み込んで展示会などに配置する場合、dataflash readコマンドは機能削除した方がよい
* また量産製品に搭載する場合、メモリプロテクトをかけることを推奨
    * さもないと、市場に出回っている製品からマイコンを剥がし、ROMライタにセットしROMライタからデータフラッシュを直接読み出すことも可能
* メモリプロテクトがかかっていても専用機材を用いて物理的にメモリ内容を読み出すアタッカも存在するかもしれない
* 従って、特に「クライアント秘密鍵」においてはRXファミリ内蔵のTrusted Secure IPを用いて暗号化した状態でデータフラッシュに保存することが望ましい
    * Amazon FreeRTOSとTrusted Secure IPの連携については鋭意開発中
        * 参考
            * [RX65N内蔵セキュリティIP Trusted Secure IP](https://github.com/renesas/amazon-freertos/wiki/RX65N%E5%86%85%E8%94%B5%E3%82%BB%E3%82%AD%E3%83%A5%E3%83%AA%E3%83%86%E3%82%A3IP-Trusted-Secure-IP)
            * [モノの証明書に紐づく秘密鍵等の重要データをTrusted Secure IPで秘匿する方法](https://github.com/renesas/amazon-freertos/wiki/%E3%83%A2%E3%83%8E%E3%81%AE%E8%A8%BC%E6%98%8E%E6%9B%B8%E3%81%AB%E7%B4%90%E3%81%A5%E3%81%8F%E7%A7%98%E5%AF%86%E9%8D%B5%E7%AD%89%E3%81%AE%E9%87%8D%E8%A6%81%E3%83%87%E3%83%BC%E3%82%BF%E3%82%92Trusted-Secure-IP%E3%81%A7%E7%A7%98%E5%8C%BF%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95)
            * [SSL TLS通信のマスターシークレットをTrusted Secure IPで秘匿する方法](https://github.com/renesas/amazon-freertos/wiki/SSL-TLS%E9%80%9A%E4%BF%A1%E3%81%AE%E3%83%9E%E3%82%B9%E3%82%BF%E3%83%BC%E3%82%B7%E3%83%BC%E3%82%AF%E3%83%AC%E3%83%83%E3%83%88%E3%82%92Trusted-Secure-IP%E3%81%A7%E7%A7%98%E5%8C%BF%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95)

