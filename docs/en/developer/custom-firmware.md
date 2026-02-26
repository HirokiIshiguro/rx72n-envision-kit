# Things to prepare
* Indispensable
    * RX72N Envision Kit × 1 unit
    * USB cable (USB Micro-B --- USB Type A) × 2 
    * Windows PC × 1 unit
        * Tools to be installed in Windows PC 
            * [e2 studio 2020-04](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
                * Initial boot sometimes takes time
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02 or later

# Prerequisite
* Complete [How to debug](../developer/how-to-debug.md) 
* If simply conventional debug and the evaluation of a separate function of RX72N are needed, refer to [Generate new project (bare metal)](../bare-metal/generate-new-project.md).

# Understand the memory map and the operation of the firmware of RX72N Envision Kit
* Understand the memory map and the operation of the firmware of RX72N Envision Kit by referring to the following  [Design memo](../developer/design-memo.md)
    * Memory map definition with the initial firmware of RX72N Envision Kit
    * Operation difference between initial firmware and after updating.

# Combine firmwares and create updater
* [How to debug](../developer/how-to-debug.md) is effective when debugging, but is not effective when mass producing.
* This is because the following two challenges exist.
    1. When mass producing, downloading takes time and effort.
    1. When operating after the mass production, data amount during updater distribution increases.(Communication fee increases)
* Create tools with following functions as countermeasures for each challenge.
    1. Create 1 sheet of MOT file for mass production by combining Bootloader, user application (for execute area) and user application(for temporary area).
    1. Create RSU file (original) for the time of mass production and operation by converting any user application binary.
        * MOT file is a hexadecimally expressed text. RSU file is a binary one. As the file size containing  2MB data for 1 side of RX72N bank, MOT file is 4MB and RSU file is 2MB.
            * When assuming  especially automatic firmware distribution via the internet, the usage fee of  data distribution server such as AWS(Amazon Web Services) is a pay-as-you-go billing system, distributed data needs to be compressed as much as possible.

# Customize firmware
* All you have to do is to change a source code and execute compile and build.
    * For example, you can try by changing the version data included in aws_demos.
        * [link](https://github.com/renesas/rx72n-envision-kit/blob/4301d18f8b23839bde70d8d2f5b428cf74a7a423/demos/include/aws_application_version.h#L34)

# How to combine firmwares
## Common
* Boot Windows application with the following path.
    * ${base_folder}/rx72n-envision-kit/vendors/renesas/tools/mot_file_converter/Renesas Secure Flash Programmer/bin/Debug/
        * Renesas Secure Flash Programmer.exe
            * Since it does not boot without dll, save the copy of the entire repository in local
                * <a href="../../images/020_pc_mot_file_convertor1.png" target="_blank"><img src="../../images/020_pc_mot_file_convertor1.png" width="480px" target="_blank"></a>

## Change cases
* Can change with the setting of Select Output Format of Initial Firm tab.
    * Case 1 = When debugging: Bank0(execute area) の RSU file
    * Case 2 = When mass producing1: Bootloader + Bank0(execute area) MOT file
    * Case 3 = When mass producing2: Bootloader + Bank0(execute area) + Bank1(temporary area)  MOT file (Same configuration with initial firmware)
* The following is the example of case 3
    * <a href="../../images/021_pc_mot_file_convertor1.png" target="_blank"><img src="../../images/021_pc_mot_file_convertor1.png" width="480px" target="_blank"></a>

# Write
* Write MOT file
    * Refer to [Revert to factory image](../quick-start/revert-to-factory-image.md)
* Write RSU file (the data created by Initial Firm) and debug.
    * Refer to [How to debug](../developer/how-to-debug.md)
