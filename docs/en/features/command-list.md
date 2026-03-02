# Outline
* Benchmark demo has command-response functions
* Commands can monitor internal state of MCU and store setting infromation

# How to execute command-response
* Please refer to the following "serial terminal demo"
    * [link](https://github.com/renesas/rx72n-envision-kit/wiki/Confirm-factory-image-behavior#benchmark-demo-bank-b)

# Command list

|version|command|argument|function|
|-----|-----|-----|-----|
|v0.9.3|version||read version|
|v0.9.3|freertos|cpuload read|read CPU usage info from FreeRTOS|
|v0.9.3|freertos|cpuload reset|reset CPU usage info from FreeRTOS|
|v1.0.1|timezone|\<timezone\>|set timezone. format \<timezone\> information is in [link](https://github.com/renesas/rx72n-envision-kit/blob/88695141fc1586bd49b38700bbd6837631175939/vendors/renesas/boards/rx72n-envision-kit/aws_demos/src/smc_gen/r_sys_time_rx/r_sys_time_rx_if.h#L46) For example, inputting UTC+09:00 means Japan Standard Time.|
|v1.0.2|reset||execute software reset|
|v1.0.2|dataflash|info|read dataflash generic info(physical size, allocated size, free size, etc)|
|v1.0.2|dataflash|read|read all settings data from dataflash|
|v1.0.2|dataflash|write aws clientprivatekey|write client private key(PEM format) data to connect to AWS. Terminal will wait your input after this command. You can cancel input mode to use "exit" or "quit".|
|v1.0.2|dataflash|write aws clientcertificate|write client certificate data(PEM format) to connect to AWS. Terminal will wait your input after this command. You can cancel input mode to use "exit" or "quit".|
|v1.0.2|dataflash|write aws codesignercertificate|write firmware integrity check public key certificate data(PEM format) when executing Amazon FreeRTOS OTA. Terminal will wait your input after this command. You can cancel input mode to use "exit" or "quit".|
|v1.0.2|dataflash|write aws mqttbrokerendpoint <mqtt_broker_end_point>|write MQTT Broker Endpoint to connect to AWS.|
|v1.0.2|dataflash|write aws iothingname <iot_thing_name>|write IoT Thing name to connect to AWS.|
|v1.0.3|dataflash|erase|erase all data stored into dataflash|
|v1.0.4|dataflash|write tcpsendperformanceserveripaddress <ip_address>|Register the TCP send performance measurement server IP address. Example of <ip_address>: 192.168.1.206|
|v1.0.4|dataflash|write tcpsendperformanceserverportnumber <port_number>|Register the TCP send performance measurement server Port number. Example of <port_number>: 5001|
|v2.0.0|dataflash|write tracealyzerserveripaddress <ip_address>|Register the Tracealyzer server IP address. Example of <ip_address>: 192.168.1.206|
|v2.0.0|dataflash|write tracealyzerserverportnumber <port_number>|Register the Tracealyzer server Port number. Example of <port_number>: 12000|
|v2.1.0|touch|\<x\> \<y\>|Issue a touch event at coordinates (x, y). 0 <= x < 480, 0 <= y < 272. Used for GUI button automation|
|v2.1.0|touch|any|Issue a touch event at screen center (240, 136). Used to pass through splash screen at startup|
|v2.1.0|sdcard|list|List all files on SD card (filename and size)|
|v2.1.0|sdcard|write \<filename\> \<size\>|Receive binary data via UART and write to SD card. Transfer controlled by handshake protocol (READY/W/DONE)|
|v2.1.0|sdcard|delete \<filename\>|Delete a file from SD card|