# Things to prepare
* Indispensable
    * RX72N Envision Kit × 1 unit
    * USB cable (USB Micro-B --- USB Type A) × 3  
    * LAN cable (must be connected to network capable of internet connection ) × 1 
    * [USB-serial conversion PMOD module](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/) × 1 
    * Windows PC × 1 unit
        * Tool which is installed in Windows PC 
            * [e2 studio 2020-04](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html) or later
                * First boot sometimes takes time.
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.01 or later
            * Operation has been confirmed with [Tera Term](https://osdn.net/projects/ttssh2/) 4.105
                *Turn off [High-speed file transfer with serial connection](https://teratermproject.github.io/manual/5/en/setup/teraterm-trans.html#FileSendHighSpeedMode): FileSendHighSpeedMode=off 
                    * Tera Term -> Setting -> Read setting -> Open TERATERM.INI  with text editor -> Change setting -> Save -> Reboot Tera Term

# Prerequisite
* FreeRTOS tutorial [Register device on AWS IoT](https://github.com/renesas/amazon-freertos/wiki/Register-device-to-AWS-IoT)  must be completed
    * A string of IoT endpoint of your AWS account has been obtained.
        * Example: a164xxxxxxxxxx-ats.iot.ap-northeast-1.amazonaws.com
    * A string of "Name of thing" for your RX72N Envision Kit has been obtained.
        * Example: rx72n_envision_kit
    *Have obtained files for certificate/public key/private key for "thing" for your RX72N Envision Kit to access AWS
* Complete each prerequisite of [FreeRTOS Over-the-Air Updates](https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html) 
    * Mainly introduces points to note about actual operation for each item as of June 14, 2020

# Keyword
* [FreeRTOS Over-the-Air Updates](https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html) has the following keywords.
* There are a name required to be input for keyword and a value specified for each account. 
* It's helpful, if you paste keywords on text editor and list the name and value as you proceed the steps 
* As the code for access policy especially explains these keywords as synonym, you need to rewrite it by yourself before applying policy.
* This article defines names and values for keywords as follows.
* If each item requests to input name, it's preferable to input the name which is defined here.
```
AWS account ID: 211xxxxxxxxx (x=cipher)
IAM user: rx72n-envision-kit
S3 bucket: rx72n-envision-kit
OTA service role service roll: rx72n-envision-kit-ota
OTA service role IAM access policy: rx72n-envision-kit-ota-iam
OTA service role S3 bucket access policy: rx72n-envision-kit-ota-s3
OTA user policy: rx72n-envision-kit-ota-user-policy
IAM user code signing operation access policy：rx72n-envision-kit-iam-code-signer
```

# How to look up AWS account ID
*A sequence which is indicated on the bottom left of the  [IAM console](https://console.aws.amazon.com/iam/home) screen is an account ID of AWS

# Each prerequisite of [FreeRTOS Over-the-Air Updates](https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html) 
* [Create an Amazon S3 bucket to store your update](https://docs.aws.amazon.com/freertos/latest/userguide/dg-ota-bucket.html)
    * 5.Regarding "Select [Next (on to the next)]  and accept the access permission of default.", there is no specific setting item.
* [Create an OTA Update service role](https://docs.aws.amazon.com/freertos/latest/userguide/create-service-role.html)
    * 7.Before "Select [Next: Tags (Next steps: Tags)] ", "[Next: Access Control (Next steps: access restriction)] " seems to be necessary, but any setting is not necessary at this point.
* [Create an OTA user policy](https://docs.aws.amazon.com/freertos/latest/userguide/create-ota-user-policy.html)
    * IAM user needs to be registered beforehand
        *In  [IAM console](https://console.aws.amazon.com/iam/home) select "user" and press "add user" button
        * IAM user name is rx72n-envision-kit.
        * Select "Access by program" as access type.
        * You may select default for other items.
        * After this follow [Create an OTA user policy](https://docs.aws.amazon.com/freertos/latest/userguide/create-ota-user-policy.html) 
* [Create a code-signing certificate](https://docs.aws.amazon.com/freertos/latest/userguide/ota-code-sign-cert.html)
    * As Renesas is now obtaining the certificate including OTA with RX65N, it does not appear on the  introductory articles and setting items on AWS as AWS official.
    * Follow the items of [Creating a code-signing certificate for custom hardware](https://docs.aws.amazon.com/freertos/latest/userguide/ota-code-sign-cert-other.html) to create a code-signing certificate and register on AWS Certificate Manager.
        * [Create a code-signing certificate](https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8#openssl%E3%81%A7%E3%81%AEecdsasha256%E7%94%A8%E3%81%AE%E9%8D%B5%E3%83%9A%E3%82%A2%E7%94%9F%E6%88%90%E6%96%B9%E6%B3%95)
            * [link](https://github.com/renesas/rx72n-envision-kit/tree/master/sample_keys) provides samples which have been created for RX72N Envision Kit.
        * [Creating a code-signing certificate for custom hardware](https://docs.aws.amazon.com/freertos/latest/userguide/ota-code-sign-cert-other.html) introduces a command line as a method to register a certificate on AWS Certificate Manager,but it can be imported from the AWS IoT Core screen, accordingly, no operation is needed at this point.
            * For reference: [AWS Certificate Manager](https://ap-northeast-1.console.aws.amazon.com/acm/home?region=ap-northeast-1) 
* [Grant access to code signing for AWS IoT](https://docs.aws.amazon.com/freertos/latest/userguide/code-sign-policy.html)
    * No special notes
* [Download FreeRTOS with the OTA library](https://docs.aws.amazon.com/freertos/latest/userguide/ota-download-freertos.html)
    * The below is about the case in which AWS certificate has been obtained, but RX72N Envision Kit has not obtained the AWS certificate yet, accordingly follow the below steps 

# Firm update steps by OTA
* Refer to "step summary" of Renesas Amazon FreeRTOS wiki OTA explanation page [Method to check actual machine operation](https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8#%E5%AE%9F%E6%A9%9F%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95) .
    * Points to note
        * Read RX65N RSK as RX72N Envision Kit, RX65N as RX72N.
        * Read user_application as aws_demos.
        * Public key for bootloader in step 5 has already been embedded in source code.
        * Parameters mentioned in step 3 and public key for application in step 6 need to be input via UART as for RX72N Envision Kit.
        * Parameters inputted via UART are stored in data flush and will not disappear even if the power supply of RX72N Envision Kit is turn off.
        * In addition, as the previous condition is maintained after firmware update, adjustment is not needed every time compile is performed.
* Parameters can be inputted from the USB connector of CN8
* When checking operation, the progress(Amazon FreeRTOS log) of OTA is outputted from USB connector
    *  It is preferable to connect [USB-Serial conversion PMOD module](https://store.digilentinc.com/pmod-usbuart-usb-to-uart-interface/)  and monitor with Tera Term.
        * Refer to the following for the connection method of CN6 and CN8 and Tera Term setting.
            * [Boot benchmark demo](https://github.com/renesas/rx72n-envision-kit/wiki/Confirm-factory-image-behavior#benchmark-demo)

# Method to input parameters in step 3 and public key for application in step 6
* Proceed to step 19 of "step summary" of Renesas Amazon FreeRTOS wik OTA explanation page, [Method to check actual machine](https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8#%E5%AE%9F%E6%A9%9F%E5%8B%95%E4%BD%9C%E7%A2%BA%E8%AA%8D%E6%96%B9%E6%B3%95) （Source code rewriting in step 3 and step 6 is not necessary）
* Check communication with CN8 with Tera Term (In default state, "RX72N Envision Kit" and prompt appear after boot loader log and becomes input state)
## Input client secret key
*Enter "dataflash write aws clientprivatekey" and press enter key
* Shift to waiting for input state
* Input client secret key: Open the client secret key（3axxxxxxxx-private.pem.key） created by AWS IoT Core with text editor and copy and paste on Tera Term
*Check that  "stored data into dataflash correctly" is displayed.
```
$ RX72N Envision Kit
$ dataflash write aws clientprivatekey
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAzhY82YODydQYFH/yFZONXFYMNJ86US+Ph+snfsinjFFU3kOp
 :
 : (Omitted)
 :
5M9Nxhh8FDzNJibzbLSZQHJNgEu9nufrOkLLxv/84heYH/W/Ako=
-----END RSA PRIVATE KEY-----
stored data into dataflash correctly.
```
## Input client certificate
* Enter "dataflash write aws clientcertificate" press enter key
* Shift to waiting for input
* Input client certificate: Open client certificate（3axxxxxxxx-certificate.pem.crt） created with AWS IoT Core with text editor and copy and paste it on Tera Term
  * NOTICE: Return code is only "LF".
* Check that "stored data into dataflash correctly." is displayed.
```
RX72N Envision Kit
$ dataflash write aws clientcertificate
-----BEGIN CERTIFICATE-----
MIIDWTCCAkGgAwIBAgIUWNAUkpzF4GO909IxarCG1nLaXO8wDQYJKoZIhvcNAQEL
 :
 : (Omitted)
 :
UB2bnt0RxcqXtoihQ2KgWWWW699CWKt4EyPoCgxuQ04P4pzlmF60BbESpUfm
-----END CERTIFICATE-----
stored data into dataflash correctly.
```
## Input certificate of public key to inspect code
* Enter "dataflash write aws codesignercertificate" and press "enter key"
* Shift to waiting for input
* Input certificate of public key to inspect code: Open （secp256r1.crt）in sample keyring of RX72N Envision Kit with text editor  and copy and paste on Tera Term.
  * NOTICE: Return code is only "LF".
*Check that "stored data into dataflash correctly" is displayed.
```
$ dataflash write aws codesignercertificate
-----BEGIN CERTIFICATE-----
MIICYDCCAgYCCQDqyS1m4rjviTAKBggqhkjOPQQDAjCBtzELMAkGA1UEBhMCSlAx
 :
 : (Omit)
 :
gQIhAO75WVGyGt58QCGNx3wMcbaDgJ4Xpqj0SWTWdxdz0jh1
-----END CERTIFICATE-----
stored data into dataflash correctly.
```
## Input IoT end point
* Enter "dataflash write aws mqttbrokerendpoint <mqtt_broker_endpoint> " and press  enter key
* <mqtt_broker_endpoint> can be checked later below.
    * [Check AWS IoT endpoint](https://github.com/renesas/amazon-freertos/wiki/Register-device-to-AWS-IoT#check-aws-iot-endpoints)
* Check that "stored data into dataflash correctly" is displayed.
```
$ dataflash write aws mqttbrokerendpoint a25xxxxxxxxxxxx-ats.iot.ap-northeast-1.amazonaws.com
stored data into dataflash correctly.
```
## Input the name of "thing"
* Enter "dataflash write aws iotthingname <iot_thing_name>" and press enter key.
* <iot_thing_name>  is the name of "thing" created below.
    * [Register device "thing" on AWS IoT](https://github.com/renesas/amazon-freertos/wiki/Register-device-to-AWS-IoT#register-your-device-thing-with-aws-iot)
  * NOTICE: Return code is only "LF".
* Check that "stored data into dataflash correctly." is displayed.
```
$ dataflash write aws iotthingname rx72n_envision_kit
stored data into dataflash correctly.
```
## Check if parameters are written correctly
* Display parameters which have been written with dataflash read command.
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
 :(The rest is omitted)
```

## If parameters stored in data flash become abnormal, all of them can be deleted with the following command.
```
$ dataflash erase
completed erasing all flash.
```

# Points to note
* "Client certificate" and "client secret key" stored in data flash is equivalent to "ID" and "Password" of user authentication.
* As "client certificate" and "client secret key" are placed in data flash as plaintext in this system, they are easily read out with dataflash read command from the outside.
* If an attacker abuses this and illegally log into the AWS account and a large amount of communication occurs, the AWS account might receive a large amount of charge.
* Accordingly, if embedding into a demo set and displaying at exhibition, it's preferable to delete the function of dataflash read command. 
* Moreover, if installing into mass produced products,apllying memory protection is recommended
    * Otherwise, MCU could be removed from the products sold in the market, and set into a ROM writer to directly read out data flash from the ROM writer.
* There might be an attacker who read out memory contents physically by using dedicated equipment even if memory protection is applied.
*Accordingly, it is preferable to store especially "client secret key" in data flash by encoding it with Trusted Secure IP with RX family
    * Now eagerly trying to find a way out of partnership over Trusted Secure IP with Amazon FreeRTOS.
        * Reference
            * [RX65N-mounted security IP Trusted Secure IP](https://github.com/renesas/amazon-freertos/wiki/RX65N%E5%86%85%E8%94%B5%E3%82%BB%E3%82%AD%E3%83%A5%E3%83%AA%E3%83%86%E3%82%A3IP-Trusted-Secure-IP)
            * [Method to conceal the important data of secret key linked to certificate of thing with Trusted Secure IP](https://github.com/renesas/amazon-freertos/wiki/%E3%83%A2%E3%83%8E%E3%81%AE%E8%A8%BC%E6%98%8E%E6%9B%B8%E3%81%AB%E7%B4%90%E3%81%A5%E3%81%8F%E7%A7%98%E5%AF%86%E9%8D%B5%E7%AD%89%E3%81%AE%E9%87%8D%E8%A6%81%E3%83%87%E3%83%BC%E3%82%BF%E3%82%92Trusted-Secure-IP%E3%81%A7%E7%A7%98%E5%8C%BF%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95)
            * [Method to conceal SSL TLS communication master secret with Trusted Secure IP](https://github.com/renesas/amazon-freertos/wiki/SSL-TLS%E9%80%9A%E4%BF%A1%E3%81%AE%E3%83%9E%E3%82%B9%E3%82%BF%E3%83%BC%E3%82%B7%E3%83%BC%E3%82%AF%E3%83%AC%E3%83%83%E3%83%88%E3%82%92Trusted-Secure-IP%E3%81%A7%E7%A7%98%E5%8C%BF%E3%81%99%E3%82%8B%E6%96%B9%E6%B3%95)
