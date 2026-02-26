# Introduction

* This section describes the design philosophy of RX72N Envision Kit initial firmware and the information necessary to customize initial firmware enabling users to conduct their original experimentation. 

# A person who are writing a memo
*  hiroki.ishiguro.fv@renesas.com

# System design
* RX72N basic information
    * Link to data sheet and hardware manual
* RX72N Envision Kit basic information
    * System block diagram
    * Link to circuit diagram
* About the mechanism of Bootloader/firmware update which are the basic part of the system.
    * https://github.com/renesas/amazon-freertos/wiki/OTA%E3%81%AE%E6%B4%BB%E7%94%A8
* System for screen display block
    * Summarize emWin
* Device driver
    * Introduce RX Driver Package

# Memory map
* Data flash: RX72N MCU specifications
```
 +---------------------------------+ 0x00100000 +
 |                                 |            |
 |       user area                 |   <32KB>   | 
 |                                 |            |
 +---------------------------------+ 0x00108000 +
```
* Data flash:Memory map definition with RX72N Envision Kit initial firmware
```
                                                                             (section name)
+---------------------+---------------------------------------+ 0x00100000 + C_BOOTLOADER_KEY_STORAGE
|  const data of      | root/integrity check keys             |   <1KB>    | 
|  boot loader        +---------------------------------------+ 0x00100400 + C_BOOTLOADER_KEY_STORAGE_MIRROR
|                     | root/integrity check keys mirror      |   <1KB>    | 
+---------------------+---------------------------------------+ 0x00100800 + C_PKCS11_STORAGE
|                     | Amazon FreeRTOS PKCS const data       |   <8KB>    | 
|  const data of      +---------------------------------------+ 0x00102800 + C_PKCS11_STORAGE_MIRROR
|  user application   | Amazon FreeRTOS PKCS const data mirror|   <8KB>    | 
|                     +---------------------------------------+ 0x00104800 + C_SYSTEM_CONFIG 
|                     | System Config Data                    |   <6KB>    | 
|                     +---------------------------------------+ 0x00106000 + C_SYSTEM_CONFIG_MIRROR
|                     | System Config Data mirror             |   <6KB>    | 
|                     +---------------------------------------+ 0x00107800 +
|                     | free area for user application        |   <2KB>    | 
|---------------------+---------------------------------------+ 0x00108000 +
```
* Code flash: RX72N MCU specifications
```
 +---------------------------------+ 0xFFC00000 +
 |                                 |            |
 |       temporary area            |  <2048KB>  | bank1
 |                                 |            |
 +---------------------------------+ 0xFFE00000 +
 |                                 |            |
 |       execute area              |  <2048KB>  | bank0
 |                                 |            |
 +---------------------------------+ 0xFFFFFFFF +
```
* Code flash:Memory map definition with RX72N Envision Kit initial firmware
```
 +----------------------+----------------------+----------------------+ 0xFFC00000+-------+
 |                      |                      |  header              | <768B>    |       |
 |                      |  buffer              +----------------------+ 0xFFC00300|       |
 |  temporary area      |                      |  contents            | <~1791KB> | bank1 |
 |                      +----------------------+----------------------+ 0xFFDC0000|       |
 |                      |  Bootloader(mirror)  |  contents            | <256KB>   |       |
 +----------------------+----------------------+----------------------+ 0xFFE00000+-------+
 |                      |                      |  header              | <768B>    |       |
 |                      |  user application    +----------------------+ 0xFFE00300|       |
 |  execute area        |                      |  contents            | <~1791KB> | bank0 |
 |                      +----------------------+----------------------+ 0xFFFC0000|       |
 |                      |  Bootloader          |  contents            | <256KB>   |       |
 +----------------------+----------------------+----------------------+ 0xFFFFFFFF+-------+
```

# Operation difference between initial firmware and after updating
* Initial firmware
    * Sports game has been installed in the execute area.
    * Benchmark has been installed in the temporary area.
    * Both benchmark and sports game have a bank swap function, enabling to boot the both areas
    * Bootloader takes on the responsibility of integrity check mechanism after updating as well as bank swap for restoration in the case of installing fraudulent firmware or when necessary.
* Firmware after updating
    * A user application of any version has been installed in the execute area.
    * Temporary area is a blank state.
    * A user application of any version has an update function. Install the new user application in the temporary area when updating.
    * Bootloader takes on the responsibility of integrity check mechanism after updating as well as bank swap for restoration in the case of installing fraudulent firmware or when necessary.
