Welcome to the rx72n-envision-kit wiki!
* Following contents include English only.
    * 日本語ページはこちら: [ホーム](../ja/README.md)


----

# Outline 
* You can confirm RX72N performance, functionality to confirm RX72N Envision Kit initial firmware behavior.
* Performance
    * R/W performance to SD card using SDHI(SD Host Interface)
    * Firmware update performance via SD card includes update firmware 
* Functionality
    * Function for display using DRW2D, GLCDC
    * Function for display using emWin from Segger
* You can add following demo by using firmware update feature
    * Already developed update firmware
        * Confirming Crypto performance of Trusted Secure IP (that can handle advanced key management mechanism) inside of RX72N chip
        * OTA Firmware update performance via Amazon Web Services includes update firmware 
        * Audio solution using D2 Audio chip(Renesas) MEMS mic
    * Now developing following update firmware
        * Wireless LAN solution using ESP32(Espressif)
        * External storage solution using QSPI serial flash(Macrinix)
* Please refer to FreeRTOS for Renesas info
    * https://github.com/renesas/amazon-freertos

# Quick Start Guide
1. [Confirm factory image behavior](quick-start/confirm-factory-image-behavior.md)
1. [Update firmware from SD card](quick-start/update-firmware-from-sd-card.md)
1. [Revert to factory image](quick-start/revert-to-factory-image.md)
# Additional
1. [OTA via AWS with FreeRTOS](features/ota-via-aws-with-freertos.md)
1. [Network Benchmark](features/network-benchmark.md)
1. [How to use Tracealyzer](features/how-to-use-tracealyzer.md)
1. [D2 audio](features/d2-audio.md)
1. [MEMS mic](features/mems-mic.md)
1. [ESP32](features/esp32.md)
1. [SSL acceleration by Trusted Secure IP(TSIP)](features/ssl-acceleration-by-trusted-secure-ip-tsip.md)
1. [Command list](features/command-list.md)
# For Developer
### initial firmware base
1. [How to debug](developer/how-to-debug.md)
1. [Custom firmware](developer/custom-firmware.md)
1. [Trouble Shooting](developer/trouble-shooting.md)
### new project base (bare metal)
1. [Generate new project (bare metal)](bare-metal/generate-new-project.md)
1. [SCI](bare-metal/sci.md)
1. [Trusted Secure IP Driver](bare-metal/trusted-secure-ip-driver.md)
1. [QSPI Serial flash driver (for Macronix)](bare-metal/qspi-serial-flash-driver.md)
1. [Ether TCP/IP](bare-metal/ether-tcp-ip.md)
1. [Ether TCP/IP Web Server](bare-metal/ether-tcp-ip-web-server.md)
1. [SDHI SD Card Driver Filesystem](bare-metal/sdhi-sd-card-driver-filesystem.md)
1. [GLCDC DRW2D emWin (Segger GUI Middleware)](bare-metal/glcdc-drw2d-emwin.md)
1. [SSI Audio playback and recording](bare-metal/ssi-audio.md)
### new project base (FreeRTOS(Kernel Only))
1. [Generate new project (FreeRTOS(Kernel Only))](freertos/generate-new-project-kernel-only.md)
1. [Application of queue Serialization of print debug](freertos/queue-serialization-of-print-debug.md)
### new project base (FreeRTOS(with IoT Libaries))
1. [Generate new project (FreeRTOS(with IoT Libaries))](freertos/generate-new-project-with-iot-libraries.md)
# Table of firmware for update
* How to write firmware = [Update firmware from SD card](quick-start/update-firmware-from-sd-card.md)

| Firmware version | Download | Changes | tools version |
| ------------- | ------------- | ------------- | ------------- |
| v2.0.2 | <a href="../../bin/updata/v202/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Enabled FPS performance. | e2 studio 2023-01<br>cc-rx v3.04 |
| v2.0.1 | <a href="../../bin/updata/v201/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Fixed Tracealyzer server IP address/portno registration issue | |
| v2.0.0 | <a href="../../bin/updata/v200/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Updated Amazon FreeRTOS to 202203.00<br>(2)Added Tracealyzer lib<br>(3)Exchange SNTP client lib to AWS one<br>(4)Update emWin lib supports AppWizard project<br>This verson cannot be used due to image verify would fail on firmware update sequence update sequence. | |
| v1.0.6 | <a href="../../bin/updata/v106/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Fixed bug on Dataflash handling | |
| v1.0.5 | <a href="../../bin/updata/v105/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Enabled Amazon FreeRTOS system log | |
| v1.0.4 | <a href="../../bin/updata/v104/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Added TCP/IP benchmark | |
| v1.0.3 | <a href="../../bin/updata/v103/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Added dataflash all erase command | |
| v1.0.2 | <a href="../../bin/updata/v102/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Added Amazon FreeRTOS OTA related demo<br>(2)Remove serial terminal display, and system log display | |
| v1.0.1 | <a href="../../bin/updata/v101/userprog.rsu" download="userprog.rsu" >userprog.rsu</a> | (1)Added CPU usage info<br>(2)Added updating time info from Internet | |

* Please save as file with right click
* Erase the sports games bank when updating, and will install only newer firmware
* Please refer to [Revert to factory image](quick-start/revert-to-factory-image.md) if you would like to revert to factory image

# Initial firmware
* How to write firmware = [Revert to factory image](quick-start/revert-to-factory-image.md)

| Firmware version | Download |
| ------------- | ------------- |
| v0.9.3 | <a href="../../bin/factory_image/v100_20200214/userprog.mot" download="userprog.mot" >userprog.mot</a> |

* Please save as file with right click

# Standalone Demo Firmware
* How to write firmware = [Revert to factory image](quick-start/revert-to-factory-image.md)
  * Please exchange the word from "initial firmware" to "standalone demo firmware" when you read this link.

| Name of demo firmware | Download | document | demo movie |
| ------------- | ------------- | ------------- | ------------- |
| Voice recognition / speech and LCD solution using RX72N Envision kit | <a href="../../bin/standalone_demo_firmware_image/voice_recognition_and_lcd/rx72n_voice_demo.mot" download="rx72n_voice_demo.mot" >rx72n_voice_demo.mot</a> | [link](https://www.renesas.com/document/scd/voice-recognition-speech-and-lcd-solution-using-rx72n-envision-kit-rev100-sample-code?language=ja&r=1169186) | N/A | 
| Using Quick-Connect IoT to Send Sensor Information to Amazon Web Services from RX72N Envision Kit Running FreeRTOS | Please download right side link and build it and write generated mot file | [link](https://www.renesas.com/document/scd/rx72n-group-using-quick-connect-iot-send-sensor-information-amazon-web-services-rx72n-envision-kit?language=ja&r=1169186)  | now creating |

* Please save as file with right click
* Other sample code for RX72N Envision Kit exists on "document" table on following product page.
  * https://www.renesas.com/products/microcontrollers-microprocessors/rx-32-bit-performance-efficiency-mcus/rx72n-envision-kit-rx72n-envision-kit

