# introduction
* This page's contents are not implemented in F/W.
* In future F/W can realize demo behavior and TLS communication benchmark, etc.
* Not implemented into RX72N Envision Kit F/W, but unit function has been developed like:

# outline
* RX family has a model which installs security IP called Trusted Secure IP
* RX72N Envision Kit adopts the model.
* Trusted Secure IP is a cipher circuit in plain words.
* A cipher circuit often refers to those which perform high-speed operation of cryptographic algorithm such as AES, RSA, SHA and elliptic curve.
* Trusted secure IP does not only have the above mentioned feature but also have a function to securely guard the key data for cryptographic operation inside the circuit.
    * When retaining the key data in the nonvolatile memory, Trusted secure IP has a mechanism to encode and pick it out of the circuit
* Furthermore, Trusted Secure IP has a flexible design to support various cipher use modes 
    * For example, a complicated mechanism of SSL (the name after standardization is TSL) can be supported by combining with a software.
        * TSL retaining "premaster secret" which is the principle of cipher key and "session key" after key exchange inside the circuit to make them completely invisible from the CPU side.
            * This maintains the system in a safe condition, because even in a state in which memory dump can be executed from outside the chip due to software malfunction, only encoded "premaster secret" and "session key" exist on the memory.
* Refer to the following page for a primitive mechanism and performance
    * https://github.com/renesas/rx72n-envision-kit/wiki/1-Trusted-Secure-IP-Driver#concept-of-trusted-secure-ip-driver-key-control

# Combination with Mbed TLS
* FreeRTOS with IoT Libraries (https://github.com/aws/amazon-freertos) uses 3rd party crypto library called Mbed TLS (https://tls.Mbed.org/).
  * Mbed TLS is Open Source library can realize SSL/TLS encrypted communication, this license is managed by Arm.
  * SSL/TLS is very famous as today, that can protect from interception, detect the falsificatoin and spoofing.
  * SSL/TLS is used for AWS IoT connection.
* No customized Mbed TLS can be used but customized Mbed TLS for TSIP has many merit.
  * TSIP can accelarate the encryption/decryption, so reducing the time for SSL/TLS handshake and communication throughput.
  * TSIP does not handle plain key so can protect user key from any threat.
* So TSIP is suitable for IoT device that has some limitation for about H/W resources etc.

# Communication throughput example
* Throughput is measuered at 1MB data transfer environment with typical cipher suite for SSL/TLS.
  * TSIP on/off and up/down condition for each cuipher suite.
  * Communication interface is Ethernet
  * Average culculateted by 5 times for 1MB data transfer
* 20 Mbps over throughput is confirmed by using TSIP
  * It satisfies the use case that needs mass data transfer use case like OTA, movie transfer.
  * SSL/TLS communication has bottoleneck that is block cipher and hash but TSIP can handle these algorithm with high-speed.
* This result is measuerd on RX65N@120MHz

|Cipher Suite|Block Cipher|Mbed TLS|Mbed TLS w/ TSIP|
|---|---|---:|---:|
|TLS_RSA_WITH_AES_128_CBC_SHA|128bit AES-CBC|Up: **6.4**Mbps <br> Down: **6.6**Mbps|Up: **25.0**Mbps <br> Down: **28.3**Mbps|
|TLS_RSA_WITH_AES_256_CBC_SHA|256bit AES-CBC|Up: **5.5**Mbps <br> Down: **5.6**Mbps|Up: **24.2**Mbps <br> Down: **27.2**Mbps|
|TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256|128bit AES-GCM|Up: **3.7**Mbps <br> Down: **3.8**Mbps|Up: **22.4**Mbps <br> Down: **29.5**Mbps|

# Implementation method
* We have prepared an application note that describes how to implement TSIP on Mbed TLS.
  * https://www.renesas.com/software-tool/trusted-secure-ip-driver
    * Trusted Secure IP driver for RX family (binary version) V1.12 or later includes a manual.
      * \r20an0548jj0112-lib-rx-tsip-security\reference_documents\en
        * r01an5880ej0100-rx-tsip.pdf
          * RX Family Implementing TLS Using TSIP Driver
