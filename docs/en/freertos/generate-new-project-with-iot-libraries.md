# Things to prepare
* Indispensable
    * RX72N Envision Kit × 1 unit
    * USB cable (USB Micro-B --- USB Type A) × 1 
    * LAN cable x 1 
    * Router connected to the internet (Supports Ethernet connection) x 1 unit
    * Windows PC × 1 unit
        * Tools to be installed in Windows PC 
            * [e2 studio 2020-07](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02 or later

# Boot e2 studio and generate new project
* File -> New -> Project
    * Wizard -> C/C++ -> C/C++ Project -> Next
        * All -> Renesas CC-RX C/C++ Executable Project
            * Project name = Input rx72n_envision_kit  -> Next
                * Toolchain Settings
                    * RTOS -> FreeRTOS(Kernel IoT Libraries)
                    * If nothing is displayed in RTOS Version, obtain RTOS package from "Manage RTOS Versions..." link.
                    * Select new one from v202002.00-rx-1.0.1 in RTOS Version.
                * Device Settings 
                    * Target Board -> EnvisionRX72N
                        * When EnvisionRX72N is selected：Target device is automatically selected
                        * When EnvisionRX72N is not selected：Target device is not automatically selected.
                            * In this case, after generating a project by selecting Custom, execute [Install Board Configuration File (BDF) of RX72N Envision Kit ](https://github.com/renesas/rx72n-envision-kit/wiki/Generate-new-project-%28FreeRTOS%28Kernel-Only%29%29#things-to-prepare)

                            * Device Settings -> Target device -> ...Button -> RX700 -> RX72N -> RX72N - 144pin -> R5F572NNHxFB (If you intend to try firmware update, select R5F572NNHxFB_DUAL)
                            * ★Future improvement★ If you try Amazon FreeRTOS OTA,  R5F572NNHxFB_DUAL needs to be selected. Fixed by BDF
                            * ★Future improvement★ Improve to enable to install BDF when generating new project, too
                * Generate Configuration -> Hardware Debug configuration -> E2 Lite (RX) -> Next
                    * Check the box of using Smart Configurator -> Exit
# How to connect
```
RX72N ENvision Kit ----(LAN cable)---Router which can be connected to the internet
 |(USB(ECN1, CN8))
PC
```

# Set debugger
* [Reference](https://github.com/renesas/rx72n-envision-kit/wiki/Generate-new-project-%28bare-metal%29#debugger-setting)

# Set TeraTerm
* [Reference](https://github.com/renesas/rx72n-envision-kit/wiki/Confirm-factory-image-behavior#benchmark-demo)
    * Refer to the item of "Connect CN8(USB Micro-B) and USB port (PC and so on) which is the communication destination using USB"
    * Refer to the item of "Boot Teraterm on Windows PC and select COM port (COMx: RSK USB Serial Port(COMx)) to connect"

# Check operation(Check network connection)
* If the following log is outputted on TeraTerm, you have succeeded.
* If IP address is obtained from DHCP like "19 4924 [IP-task] IP Address: 192.168.1.209", it has been booted normally.

```
0 1 [ETHER_RECEI] Deferred Interrupt Handler Task started
1 1 [ETHER_RECEI] Network buffers: 8 lowest 8
2 1 [ETHER_RECEI] Heap: current 234144 lowest 234144
3 1 [ETHER_RECEI] Queue space: lowest 13
4 1 [IP-task] InitializeNetwork returns OK
5 1 [IP-task] xNetworkInterfaceInitialise returns 0
6 101 [ETHER_RECEI] R_ETHER_Read_ZC2: rc = -5
7 102 [ETHER_RECEI] prvLinkStatusChange( 1 )
8 102 [ETHER_RECEI] prvEMACHandlerTask: PHY LS now 1
9 102 [ETHER_RECEI] Heap: current 233944 lowest 233344
10 193 [ETHER_RECEI] Network buffers: 7 lowest 7
11 1194 [ETHER_RECEI] Network buffers: 6 lowest 6
12 2197 [ETHER_RECEI] Network buffers: 5 lowest 5
13 3001 [IP-task] xNetworkInterfaceInitialise returns 1
14 3097 [ETHER_RECEI] Heap: current 233776 lowest 233248
15 3097 [ETHER_RECEI] Queue space: lowest 10
16 4915 [IP-task] vDHCPProcess: offer c0a801d1ip
17 4924 [ETHER_RECEI] Heap: current 233408 lowest 233208
18 4924 [IP-task] vDHCPProcess: offer c0a801d1ip
19 4924 [IP-task] IP Address: 192.168.1.209
20 4924 [IP-task] Subnet Mask: 255.255.255.0
21 4924 [IP-task] Gateway Address: 192.168.1.1
22 4924 [IP-task] DNS Server Address: 192.168.1.1
23 5024 [ETHER_RECEI] Heap: current 233888 lowest 232576
24 5100 [Tmr Svc] The network is up and running
25 5124 [ETHER_RECEI] Heap: current 231720 lowest 231648
26 5194 [ETHER_RECEI] Heap: current 229848 lowest 228496
27 6892 [Tmr Svc] Warning: the client certificate should be updated. Please see https://aws.amazon.com/freertos/getting-started/.
28 6892 [Tmr Svc] Device public key, 91 bytes:
3059 3013 0607 2a86 48ce 3d02 0106 082a
8648 ce3d 0301 0703 4200 0468 9158 27d1
6fb0 a44e adbd a718 5798 1ab5 8a7c c1c8
ad07 ddf5 ae0d e92d d2af fc43 7be8 d049
706b 7c54 3933 0ed8 88c9 1af8 9741 5277
1b4f f383 f4d9 fade 48de 91
29 6893 [iot_thread] [INFO ][DEMO][6893] ---------STARTING DEMO---------

30 6894 [ETHER_RECEI] Heap: current 212080 lowest 212080
35 6953 [ETHER_RECEI] Heap: current 207944 lowest 206720
36 7016 [iot_thread] [ERROR][NET][7016] Failed to resolve .
37 7016 [iot_thread] [ERROR][MQTT][7016] Failed to establish new MQTT connection, error NETWORK ERROR.
38 7016 [iot_thread] [ERROR][DEMO][7016] MQTT CONNECT returned error NETWORK ERROR.
39 7016 [iot_thread] [INFO ][MQTT][7016] MQTT library cleanup done.
40 7016 [iot_thread] [ERROR][DEMO][7016] Error running demo.
41 7016 [iot_thread] [INFO ][INIT][7016] SDK cleanup done.
42 7016 [iot_thread] [INFO ][DEMO][7016] -------DEMO FINISHED-------
```

# Check operation(Check AWS connection)
* To check connection with AWS, you need to embed AWS connection information on the source code and perform setting on AWS side.
* Refer to the following tutorial
    * https://github.com/renesas/amazon-freertos/wiki/Register-device-to-AWS-IoT