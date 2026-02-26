# Things to prepare
* Indispensable
    * RX72N Envision Kit × 1 unit
    * USB cable (USB Micro-B --- USB Type A) × 2 
    * Windows PC × 1 unit
        *Tools installed in Windows PC 
            * [Tracealyzer](https://percepio.com/downloadform/)
    * LAN cable × 2 
    * router × 1 unit (which operates as DHCP server)

# Prerequisite
*  Installed firmware is version v2.0.0 or later.
    * Method of writing = [Update firmware from SD card](../../quick-start/update-firmware-from-sd-card.md)
* Operation of command response has been checked
    * Refer to serial terminal demo in the following page
        * [Confirm factory image behavior](../../quick-start/confirm-factory-image-behavior.md)

# Execution Behavior
* Tracealyzer stores internal information of Realtime OS on RAM, output them by using UART, Ethernet, etc to outside of device and PC can receive them and PC can visualize this internal information.
  * For this, Tracealyzer need installing library that can gather the internal information from the device has Realtime OS.
  * In RX72N Envision Kit case we implemented this feature
    * later firmware version v.2.0.0.
    * can output the data via Ethernet.
  * RX72N Envision Kit need to know PC IP address and port number to communicate with PC
    * We can input these setting value by using command response.

# Example of setting for RX72N Envision Kit
* dataflash write tracealyzerserveripaddress 192.168.1.210
* dataflash write tracealyzerserverportnumber 12000
* ![image](https://user-images.githubusercontent.com/37968119/190856509-adf63d75-8192-4ed9-9d32-3896893d85ab.png)

# Example of setting for PC
* ![image](https://user-images.githubusercontent.com/37968119/190856426-04e876d5-0030-4a14-a48f-4116cd94df31.png)

# Execution behavior example
* ![image](https://user-images.githubusercontent.com/37968119/190855728-53eb5c33-51c3-4d99-89f1-4b8fd3d59e39.png)

# Reference
* This page introduce only how to use, and this page omit introducing how to implement Tracealyzer Library: [Tracealyzer Recorder](https://github.com/percepio/TraceRecorderSource) that is implemented in RX72N Envision Kit firmware.
* For how to implementation, please refer to following page.
  * [How to implement Tracealyzer Recorder](../../freertos/how-to-implement-tracealyzer-recorder.md)

