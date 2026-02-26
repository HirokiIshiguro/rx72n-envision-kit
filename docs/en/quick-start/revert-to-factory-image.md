# Preparing items
* must
    * RX72N Envision Kit x 1
    * USB Cable(USB Micro-B --- USB Type A) x 1
    * Windows PC x 1
* option
    * none

# Procedure for reverting to initial firmware
1. Download initial firmware
    * Download initial firmware(userprog.mot) file from following URL
        * [link](https://github.com/renesas/rx72n-envision-kit/wiki#initial-firmware)
1. Save initial firmware to your desktop
1. Set to SW1-2 OFF (lower) on RX72N Envision Kit
    * <a href="../../images/017_board_sw1.jpg" target="_blank"><img src="../../images/017_board_sw1.jpg" width="480px" target="_blank"></a>
1. Download Renesas Flash Programmer v3.06 or later
    * [link](https://www.renesas.com/products/software-tools/tools/programmer/renesas-flash-programmer-programming-gui.html)
1. Start Renesas Flash Programmer
1. File -> new project
    * Project Information
        * Microcontroller: RX72x
        * Project Name: any
        * Place: any
    * Communication
        * Tool: E2 emulator Lite
        * Interface: Fine
1. Keep default value for ID code setting, and push [OK]
1. Push [refer] button on right side of program file, and specify initial firmware(userprog.mot) downloaded on [1]
1. Push [start] button
1. Wait until finishing
1. Set to SW1-2 ON (upper) on RX72N Envision Kit
    * <a href="../../images/018_board_sw1.jpg" target="_blank"><img src="../../images/018_board_sw1.jpg" width="480px" target="_blank"></a>
1. finish
