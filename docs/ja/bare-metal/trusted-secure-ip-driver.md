# 準備する物
* 必須
    * RX72N Envision Kit × 1台
    * USBケーブル(USB Micro-B --- USB Type A) × 1 本
    * Windows PC × 1 台
        * Windows PC にインストールするツール
            * [e2 studio 2020-07](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02以降

# 前提条件
* [新規プロジェクト作成方法(ベアメタル)](../bare-metal/generate-new-project.md) を完了すること
    * 本稿では、[新規プロジェクト作成方法(ベアメタル)](../bare-metal/generate-new-project.md)で作成したLED0.1秒周期点滅プログラムにTSIP(Trusted Secure IP)のコードを追加する形で実装する

# Trusted Secure IPの特長
* 高速な暗号演算
    * 参考: [wolfSSL社によるベンチマーク](https://www.wolfssl.com/renesas-rx72n-envision-kit-supported/)
* 低消費を実現できるシステム最適
    * 参考: [チューリッヒ大学によるベンチマーク](https://digitalcollection.zhaw.ch/handle/11475/25777)
* 高度なセキュリティ性を有する暗号機能を低コストで量産製品に組み込み可能
* AES等の世界標準暗号アルゴリズムを高速に実行可能
* スマートメータの要求仕様で頻出のAES-GCMアルゴリズムをサポート
* ファームウェアのアップデートを安全に実行するための機能を提供
* RXマイコンもしくはRE、RZ用のデバイスドライバにより簡単に制御可能
* 米国標準技術研究所(NIST)の暗号モジュールの検定FIPS140-2 CMVP level3に合格できる水準のセキュリティ
  * ニュースリリース
    * https://www.renesas.com/about/press-room/renesas-rx-mcu-becomes-world-s-first-general-purpose-mcu-obtain-cmvp-level-3-certification-under
  * 合格証書
    * https://csrc.nist.gov/projects/cryptographic-module-validation-program/certificate/3849

# Trusted Secure IPドライバ 鍵管理の概念
* Trusted Secure IPではシステム上(RX72N上)およびソースコード上でユーザ鍵データを平文では扱わない特性を持たせている
* ユーザ鍵はプロビジョニング鍵を用いて暗号化される
* プロビジョニング鍵はHRK(Hidden Root Key)を用いて暗号化される
* HRKはRenesas Device Lifecycle Management (DLM) Server内部、および、Trusted Secure IP内部で守られている
* プロビジョニング鍵により暗号化されたユーザ鍵はインストールAPIを用いてTrusted Secure IP内部で守られたHRKによる暗号化(ユーザ鍵 + 乱数成分 + チップユニークID)を経て鍵生成情報化される
    * 鍵生成情報は暗号化されていることにより、ソースコード流出やファームウェア流出、ソフトウェア不具合を利用したメモリダンプ等の脅威から平文のユーザ鍵を守ることができる
    * またユーザ鍵生成情報には鍵データの属性として一般的に必要とされる以下のような情報が含まれる
        * ①改ざんチェックのための情報(MAC値)
        * ②デッドコピーを防止するためのチップユニークIDを基とした情報
        * ③リプレイアタックを防止するための乱数値を基とした情報
        * ④使用用途を限定するための属性情報
    * 鍵生成情報は各種API入力時に上述の属性情報のチェックが行われ、異常検出されるとその鍵生成情報は各種APIには受け付けられない
    * 鍵生成情報は英語およびソースコード上では KeyIndex と表現される
    * インストールAPIの具体例は R_TSIP_GenerateAes128KeyIndex() である
    * 量産において、システムの安全性向上のため、インストールAPIの入力値のひとつである暗号化されたプロビジョニング鍵はシステムから削除してから市場投入することが望ましい
    * 以下に上記鍵管理の概念を模式図で表す
        * <a href="../../images/049_tsip_system_block.png" target="_blank"><img src="../../images/049_tsip_system_block.png" width="480px" target="_blank"></a>

* ウェブダウンロード可能なTrusted Secure IPドライバはバイナリ版であり、Device Lifecycle Management (DLM) Serverを用いて暗号化済のサンプルプロビジョニング鍵を同梱している
    * \r20an0548jjxxxx-lib-rx-tsip-security\FITDemos\rx72m_rx72n_rx66n_key
        * 従ってTrusted Secure IPドライバはバイナリ版使用者はすべて同じプロビジョニング鍵となる
            * これはUser Factoryにおいて暗号化されたユーザ鍵を復号され、平文のユーザ鍵が漏洩するリスクとなる
                * 従って量産製品を検討する場合、Trusted Secure IPドライバのソースコード版とDevice Lifecycle Management (DLM) Serverを利用し、独自のプロビジョニング鍵を利用することを推奨する
* Trusted Secure IPドライバのソースコード版入手方法については、Trusted Secure IPドライバのホームページ参照
    * https://www.renesas.com/products/software-tools/software-os-middleware-driver/security-crypto/trusted-secure-ip-driver.html
    * なお、Trusted Secure IPドライバはTrusted Secure IP搭載デバイスの市販暗号除外規定適用のためバイナリ版をウェブ提供としているだけであり特段セキュリティ実装上の理由はない
    * ソースコード版においては、需要者に対し個別に取引審査を実施の後、提供となる

# 回路確認
* Trusted Secure IP動作確認では特にボード上の回路は必要としない

# スマートコンフィグレータによるTrusted Secure IP用ドライバの設定
## Trusted Secure IP用ドライバのダウンロード
* Trusted Secure IP用ドライバはまだRX Driver Packageに標準付属されていない
* 以下URLから手動ダウンロードする ★将来RX Driver Packageに同梱する★
    * https://www.renesas.com/products/software-tools/software-os-middleware-driver/security-crypto/trusted-secure-ip-driver.html
        * ダウンロードボタンからダウンロード可能

## Trusted Secure IP用ドライバソフトウェアのインストール
* ダウンロードパッケージ(ZIPファイル)を解凍し以下2ファイルをコピー
    * \r20an0548jjxxxx-lib-rx-tsip-security\FITModules\r_tsip_rx_v1.09_lib.zip
    * \r20an0548jjxxxx-lib-rx-tsip-security\FITModules\r_tsip_rx_v1.09_lib.xml
* e2 studio 管理のFITモジュールインストールフォルダに上記2ファイルをペースト
    * ペースト先は以下解説を参照
        * https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95#%E7%94%BB%E9%9D%A2%E5%87%A6%E7%90%86%E7%B3%BB%E3%81%AEfit%E3%83%A2%E3%82%B8%E3%83%A5%E3%83%BC%E3%83%AB

## コンポーネント追加
* <a href="../../images/048_e2_studio_sc.png" target="_blank"><img src="../../images/048_e2_studio_sc.png" width="480px" target="_blank"></a>
    * 上記のようにコンポーネントを追加する
        * r_tsip_rx 
    * コード生成する

## コンポーネント設定
### r_tsip_rx
* ウェブダウンロード可能なTSIPドライバ(バイナリ版)ではコンフィグ可能な項目なし

## Renesas Secure Flash Programmerによるユーザ鍵の暗号化
* 以下exeファイルを起動する
    * \r20an0548jjxxxx-lib-rx-tsip-security\tool\renesas_secure_flash_programmer\Renesas Secure Flash Programmer\bin\Debug
        * Renesas Secure Flash Programmer.exe
* 以下設定を施す
    * <a href="../../images/050_tsip.png" target="_blank"><img src="../../images/050_tsip.png" width="480px" target="_blank"></a>
        * Key Wrap タブを選択
            * MCU -> Select MCU で [RX72M] を選択 ★[RX72N]が選べないのは将来修正★
            * Key Setting -> Key Data で [0123456789abcdef0123456789abcdef] を入力 (128bitの任意の値であれば何でもよい）
                * Register ボタンを押して、入力した値がテーブルに登録されることを確認
                * 任意の数の鍵データを登録可能
                * AES以外にもRSAやECC等の鍵データも登録可能
            * provisioning key -> provisioning key File Path に 平文のプロビジョニング鍵のファイルパスを指定する
                * \r20an0548jjxxxx-lib-rx-tsip-security\FITDemos\rx72m_rx72n_rx66n_key\sample.key
            * provisioning key -> encrypted provisioning key File Path に 暗号文のプロビジョニング鍵のファイルパスを指定する
                * \r20an0548jjxxxx-lib-rx-tsip-security\FITDemos\rx72m_rx72n_rx66n_key\sample_enc.key
            * Generate Key Files ボタンを押す
                * 暗号化されたユーザ鍵のC言語ソースファイル(key_data.c, key_data.h)が出力される
                * 暗号化されたユーザ鍵のC言語ソースファイルをテキストエディタで開くと、ユーザ鍵[0123456789abcdef0123456789abcdef]の値がどこにもないことが確認できる

## 暗号化されたユーザ鍵のC言語ソースファイルをプロジェクトに登録する
* プロジェクトエクスプローラでプロジェクトファイル置き場を開く
    * プロジェクトエクスプローラ上のプロジェクト名で右クリックしてSystem Explorerを選択
        * <a href="../../images/051_e2_studio.png" target="_blank"><img src="../../images/051_e2_studio.png" width="480px" target="_blank"></a>
    * 開いたエクスプローラ内の[src]フォルダ内に暗号化されたユーザ鍵のC言語ソースファイル(key_data.c, key_data.h)をペースト

## Trusted Secure IPドライバのバイナリをプロジェクトに登録する
* 本設定は★将来バージョンで設定不要になる見込み★
* プロジェクトエクスプローラ上のプロジェクト名で右クリックしてプロパティを選択
    * <a href="../../images/052_e2_studio.png" target="_blank"><img src="../../images/052_e2_studio.png" width="480px" target="_blank"></a>
        * Trusted Secure IPドライバのバイナリをリンカに指定する
            * <a href="../../images/053_e2_studio.png" target="_blank"><img src="../../images/053_e2_studio.png" width="480px" target="_blank"></a>

## Trusted Secure IPドライバ関連の鍵データ置き場となるデータフラッシュ上のセクション設定をプロジェクトに登録する
* 本設定は★将来バージョンで設定不要になる見込み★
* プロジェクトエクスプローラ上のプロジェクト名で右クリックしてプロパティを選択
    * <a href="../../images/052_e2_studio.png" target="_blank"><img src="../../images/052_e2_studio.png" width="480px" target="_blank"></a>
        * 鍵データ置き場となるデータフラッシュ上のセクション設定をリンカに指定する
            * <a href="../../images/054_e2_studio.png" target="_blank"><img src="../../images/054_e2_studio.png" width="480px" target="_blank"></a>
            * 0x00100000番地に C_FIRMWARE_UPDATE_CONTROL_BLOCK* を登録

## main()関数のコーディング (AES128動作確認)
* 以下のように rx72n_envision_kit.c にコード追加を行う
* このコードでは、printf()の出力をRenesas Debug Virtual Consoleに出力する

```rx72n_envision_kit.c
#include <stdio.h>

#include "r_smc_entry.h"
#include "r_tsip_rx_if.h"
#include "key_data.h"
#include "r_cmt_rx_if.h"

void main(void);
void cmt_callback(void *arg);

uint8_t plain[R_TSIP_AES_BLOCK_BYTE_SIZE];
uint8_t cipher[R_TSIP_AES_BLOCK_BYTE_SIZE];

void main(void)
{
	uint32_t channel;

	tsip_aes_key_index_t tsip_aes_key_index;
	tsip_aes_handle_t tsip_aes_handle;
	uint32_t cipher_length;
	int i;

	R_CMT_CreatePeriodic(10, cmt_callback, &channel);

	R_TSIP_Open(NULL, NULL);
	R_TSIP_GenerateAes128KeyIndex(
			(uint8_t *)g_user_key_block_data.encrypted_provisioning_key,
			(uint8_t *)g_user_key_block_data.iv,
			(uint8_t *)g_user_key_block_data.encrypted_user_aes128_key,
			&tsip_aes_key_index);

	R_TSIP_Aes128EcbEncryptInit(&tsip_aes_handle, &tsip_aes_key_index);
	R_TSIP_Aes128EcbEncryptUpdate(&tsip_aes_handle, plain, cipher, sizeof(plain));
	R_TSIP_Aes128EcbEncryptFinal(&tsip_aes_handle, cipher, &cipher_length);

	printf("plain: ");
	for(i = 0; i < R_TSIP_AES_BLOCK_BYTE_SIZE; i++)
	{
		printf("%02x", plain[i]);
	}
	printf("\n");

	printf("cipher: ");
	for(i = 0; i < R_TSIP_AES_BLOCK_BYTE_SIZE; i++)
	{
		printf("%02x", cipher[i]);
	}
	printf("\n");

	while(1);
}

void cmt_callback(void *arg)
{
	if(PORT4.PIDR.BIT.B0 == 1)
	{
		PORT4.PODR.BIT.B0 = 0;
	}
	else
	{
		PORT4.PODR.BIT.B0 = 1;
	}
}
```

## 動作確認
* ビルドする
    * Duplicate Symbol のワーニングが大量に出るが無視する ★将来バージョンで改善見込み★
    * ライブラリ版故、TSIPドライバの最大容量(130KB程度)を常に消費する ★ソースコード版ではコンフィグ可能(ライブラリ生成時に工夫すれば改善するかもしれない(検討中))★
* ダウンロードする
    * https://github.com/renesas/rx72n-envision-kit/wiki/%E6%96%B0%E8%A6%8F%E3%83%97%E3%83%AD%E3%82%B8%E3%82%A7%E3%82%AF%E3%83%88%E4%BD%9C%E6%88%90%E6%96%B9%E6%B3%95#%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D
* printf()の出力先となる e2 studio の Renesas Debug Virtual Console を開いておく
    * Renesas view -> デバッグ -> Renesas Debug Virtual Console
* 実行する
    * Renesas Debug Virtual Console に以下のように出力される
```
plain: 00000000000000000000000000000000
cipher: 79abc5c23868ad84d388ce61110a6274
```

* ユーザ鍵は先述の通り[0123456789abcdef0123456789abcdef]である
* WindowsアプリのAesCrypterを使用して、cipher[79abc5c23868ad84d388ce61110a6274]をユーザ鍵[0123456789abcdef0123456789abcdef]を用いてplain[00000000000000000000000000000000]に復号する
    * [AesCrypter](https://www.vector.co.jp/soft/winnt/util/se424956.html)
        * <a href="../../images/055_aes.png" target="_blank"><img src="../../images/055_aes.png" width="480px" target="_blank"></a>

## main()関数のコーディング (主要APIの性能確認)
* AES128、SHA256、乱数生成、RSA1024鍵生成、RSA2048鍵生成、ECC P-256鍵生成の性能を計測し、実行結果をRenesas Debug Virtual Consoleに出力する
```rx72n_envision_kit.c
#include <stdio.h>

#include "r_smc_entry.h"
#include "r_tsip_rx_if.h"
#include "key_data.h"
#include "r_cmt_rx_if.h"

#define GENERATE_RSA_KEY_NUMBER 10
#define GENERATE_ECC_KEY_NUMBER 10

void main(void);
void cmt_callback(void *arg);
void cmt_1us_callback(void *arg);
void _1us_timer_reset(void);
void _1us_timer_stop(void);
void _1us_timer_start(void);
uint32_t _1us_timer_get(void);

uint8_t plain[R_TSIP_AES_BLOCK_BYTE_SIZE * 1024];
uint8_t cipher[R_TSIP_AES_BLOCK_BYTE_SIZE * 1024];
uint32_t _1us_timer;
volatile uint32_t _1us_timer_flag;

void main(void)
{
	uint32_t cmt_channel1, cmt_channel2;

	tsip_aes_key_index_t tsip_aes_key_index;
	tsip_aes_handle_t tsip_aes_handle;
	uint32_t cipher_length;
	int i;

	tsip_sha_md5_handle_t tsip_sha_md5_handle;
	uint8_t digest[R_TSIP_SHA256_HASH_LENGTH_BYTE_SIZE];
	uint32_t digest_length;
	uint32_t random;
	uint32_t tmp;
	tsip_rsa1024_key_pair_index_t tsip_rsa1024_key_pair_index;
	tsip_rsa2048_key_pair_index_t tsip_rsa2048_key_pair_index;
	tsip_ecc_key_pair_index_t tsip_ecc_key_pair_index;

	R_CMT_CreatePeriodic(10, cmt_callback, &cmt_channel1);
	R_CMT_CreatePeriodic(1000000, cmt_1us_callback, &cmt_channel2);

	R_TSIP_Open(NULL, NULL);
	R_TSIP_GenerateAes128KeyIndex(
			(uint8_t *)g_user_key_block_data.encrypted_provisioning_key,
			(uint8_t *)g_user_key_block_data.iv,
			(uint8_t *)g_user_key_block_data.encrypted_user_aes128_key,
			&tsip_aes_key_index);

	R_TSIP_Aes128EcbEncryptInit(&tsip_aes_handle, &tsip_aes_key_index);
	R_TSIP_Aes128EcbEncryptUpdate(&tsip_aes_handle, plain, cipher, sizeof(plain));
	R_TSIP_Aes128EcbEncryptFinal(&tsip_aes_handle, cipher, &cipher_length);

	printf("plain: ");
	for(i = 0; i < R_TSIP_AES_BLOCK_BYTE_SIZE; i++)
	{
		printf("%02x", plain[i]);
	}
	printf("\n");

	printf("cipher: ");
	for(i = 0; i < R_TSIP_AES_BLOCK_BYTE_SIZE; i++)
	{
		printf("%02x", cipher[i]);
	}
	printf("\n");

	_1us_timer_reset();
	_1us_timer_start();
	R_TSIP_Aes128EcbEncryptInit(&tsip_aes_handle, &tsip_aes_key_index);
	R_TSIP_Aes128EcbEncryptUpdate(&tsip_aes_handle, plain, cipher, sizeof(plain));
	R_TSIP_Aes128EcbEncryptFinal(&tsip_aes_handle, cipher, &cipher_length);
	_1us_timer_stop();
	printf("AES128 encrypt %d bytes takes %d us, throughput = %f Mbps\n", sizeof(plain), _1us_timer_get(), (float)((sizeof(plain) * 8) / (float)((float)_1us_timer_get() / (1000000))/1000000));

	_1us_timer_reset();
	_1us_timer_start();
	R_TSIP_Sha256Init(&tsip_sha_md5_handle);
	R_TSIP_Sha256Update(&tsip_sha_md5_handle, plain, sizeof(plain));
	R_TSIP_Sha256Final(&tsip_sha_md5_handle, digest, &digest_length);
	_1us_timer_stop();
	printf("SHA256 hash %d bytes takes %d us, throughput = %f Mbps\n", sizeof(plain), _1us_timer_get(), (float)((sizeof(plain) * 8) / (float)((float)_1us_timer_get() / (1000000))/1000000));

	_1us_timer_reset();
	_1us_timer_start();
	for(i = 0; i < sizeof(plain) / 4; i += 4)
	{
		R_TSIP_GenerateRandomNumber(&random);
	}
	_1us_timer_stop();
	printf("Generate random %d bytes takes %d us, throughput = %f Mbps\n", sizeof(plain), _1us_timer_get(), (float)((sizeof(plain) * 8) / (float)((float)_1us_timer_get() / (1000000))/1000000));

	tmp = 0;
	for(i = 0; i < GENERATE_RSA_KEY_NUMBER; i++)
	{
		_1us_timer_reset();
		_1us_timer_start();
		R_TSIP_GenerateRsa1024RandomKeyIndex(&tsip_rsa1024_key_pair_index);
		_1us_timer_stop();
		printf("(%2d/%2d): Generate RSA1024 key pair takes %d us\n", i + 1, GENERATE_RSA_KEY_NUMBER, _1us_timer_get());
		tmp += _1us_timer_get();
	}
	printf("---------------------------------------------------------\n");
	printf("Generate RSA1024 key pair takes %d us as average.\n", tmp / GENERATE_RSA_KEY_NUMBER);
	printf("---------------------------------------------------------\n");

	tmp = 0;
	for(i = 0; i < GENERATE_RSA_KEY_NUMBER; i++)
	{
		_1us_timer_reset();
		_1us_timer_start();
		R_TSIP_GenerateRsa2048RandomKeyIndex(&tsip_rsa2048_key_pair_index);
		_1us_timer_stop();
		printf("(%2d/%2d): Generate RSA2048 key pair takes %d us\n", i + 1, GENERATE_RSA_KEY_NUMBER, _1us_timer_get());
		tmp += _1us_timer_get();
	}
	printf("---------------------------------------------------------\n");
	printf("Generate RSA2048 key pair takes %d us as average.\n", tmp / GENERATE_RSA_KEY_NUMBER);
	printf("---------------------------------------------------------\n");

	tmp = 0;
	for(i = 0; i < GENERATE_ECC_KEY_NUMBER; i++)
	{
		_1us_timer_reset();
		_1us_timer_start();
		R_TSIP_GenerateEccP256RandomKeyIndex(&tsip_ecc_key_pair_index);
		_1us_timer_stop();
		printf("(%2d/%2d): Generate ECC P-256 key pair takes %d us\n", i + 1, GENERATE_ECC_KEY_NUMBER, _1us_timer_get());
		tmp += _1us_timer_get();
	}
	printf("---------------------------------------------------------\n");
	printf("Generate ECC P-256 key pair takes %d us as average.\n", tmp / GENERATE_ECC_KEY_NUMBER);
	printf("---------------------------------------------------------\n");

	while(1);
}

void cmt_callback(void *arg)
{
	if(PORT4.PIDR.BIT.B0 == 1)
	{
		PORT4.PODR.BIT.B0 = 0;
	}
	else
	{
		PORT4.PODR.BIT.B0 = 1;
	}
}

void cmt_1us_callback(void *arg)
{
	if(_1us_timer_flag)
	{
		_1us_timer++;
	}
}

void _1us_timer_reset(void)
{
	_1us_timer = 0;
}

void _1us_timer_stop(void)
{
	_1us_timer_flag = 0;
}

void _1us_timer_start(void)
{
	_1us_timer_flag = 1;
}

uint32_t _1us_timer_get(void)
{
	return _1us_timer;
}
```

* 出力結果

```
plain: 00000000000000000000000000000000
cipher: 79abc5c23868ad84d388ce61110a6274
AES128 encrypt 16384 bytes takes 667 us, throughput = 196.509750 Mbps
SHA256 hash 16384 bytes takes 442 us, throughput = 296.542999 Mbps
Generate random 16384 bytes takes 5120 us, throughput = 25.600000 Mbps
( 1/10): Generate RSA1024 key pair takes 540086 us
( 2/10): Generate RSA1024 key pair takes 334216 us
( 3/10): Generate RSA1024 key pair takes 768522 us
( 4/10): Generate RSA1024 key pair takes 264502 us
( 5/10): Generate RSA1024 key pair takes 1312443 us
( 6/10): Generate RSA1024 key pair takes 614302 us
( 7/10): Generate RSA1024 key pair takes 96265 us
( 8/10): Generate RSA1024 key pair takes 72716 us
( 9/10): Generate RSA1024 key pair takes 1173135 us
(10/10): Generate RSA1024 key pair takes 219992 us
---------------------------------------------------------
Generate RSA1024 key pair takes 539617 us as average.
---------------------------------------------------------
( 1/10): Generate RSA2048 key pair takes 5514318 us
( 2/10): Generate RSA2048 key pair takes 8576225 us
( 3/10): Generate RSA2048 key pair takes 6450949 us
( 4/10): Generate RSA2048 key pair takes 13272585 us
( 5/10): Generate RSA2048 key pair takes 5337163 us
( 6/10): Generate RSA2048 key pair takes 9399025 us
( 7/10): Generate RSA2048 key pair takes 6139061 us
( 8/10): Generate RSA2048 key pair takes 5138732 us
( 9/10): Generate RSA2048 key pair takes 9920193 us
(10/10): Generate RSA2048 key pair takes 5580538 us
---------------------------------------------------------
Generate RSA2048 key pair takes 7532878 us as average.
---------------------------------------------------------
( 1/10): Generate ECC P-256 key pair takes 1305 us
( 2/10): Generate ECC P-256 key pair takes 1277 us
( 3/10): Generate ECC P-256 key pair takes 1293 us
( 4/10): Generate ECC P-256 key pair takes 1298 us
( 5/10): Generate ECC P-256 key pair takes 1282 us
( 6/10): Generate ECC P-256 key pair takes 1253 us
( 7/10): Generate ECC P-256 key pair takes 1303 us
( 8/10): Generate ECC P-256 key pair takes 1276 us
( 9/10): Generate ECC P-256 key pair takes 1304 us
(10/10): Generate ECC P-256 key pair takes 1298 us
---------------------------------------------------------
Generate ECC P-256 key pair takes 1288 us as average.
---------------------------------------------------------
```