# <a name="purpose"></a>Purpose
* Give an outline of how to use [Smart Configurator for RX](https://www.renesas.com/products/software-tools/tools/solution-toolkit/smart-configurator.html)
* Describe based on the operation of e2 studio 2020-07 and CS+ V8.03（Recheck in CS+ 64-bit version）
* Call Smart Configurator "SC" in this page

# <a name="summary"></a>Outline of Smart Configurator
## What is Smart Configurator?
* SC is a utility with the concept of "Enables to combine Software freely"
* SC mainly provides the following functions.
  * Introduce and set driver software and middleware utilizing RX MCU peripheral functions<br>（These soft/middleware are provided as the following components）

    * Firmware Integration Technology (FIT) module
    * Code generation（CG）module
  * Clock and pin setting with GUI
  * Function to generate source
* Refer to the following applications for details
  * [RX Smart Configurator User Guide: e2 studio version](https://www.renesas.com/doc/products/tool/doc/016/r20an0470jj0120-cspls-sc.pdf)
  * [RH850 Smart Configurator User Guide: CS+version](https://www.renesas.com/doc/products/tool/doc/016/r20an0470jj0120-cspls-sc.pdf)
## <a name="merit"></a>In Timer system represented by CMT and communication system represented by SCI, its setting values need to be adjusted by software according to the clock speed of clock signal wired to each.
* Users originally need to perform the coding of this software by referring to the MCU manual. However, as it has a wide variety of setting items, we have prepared a mechanism to support this by tools like SC.
* Users (especially application designer) can instruct from software to hardware without worrying about what MHz the clock source is or how the setting inside PLL is, for example “baud rate is 115200bps” with API level, thereby improving software development efficiency.
* In addition, designers with full knowledge of RX family products perform development and maintenance (continuous bug fix) of the driver software for RX family-mounted circuit, such as CMT, SCI, Ether, USB and SDHI with API design in “FIT module” format for major RX group  and distribute FIT module packaged by one as “RX Driver Package”
* Therefore, users can focus on the application development without worrying about detailed hardware differences in RX family products and hardware errata information.

# Generic document
* https://www.renesas.com/document/apn/renesas-e-studio-smart-configurator-application-examples-cmt-ad-sci-dma-usb

# <a name="how_to_use"></a>How to use
## <a name="creation_sc_project"></a>Create project with SC and boot SC
### <a name="creation_sc_project_e2"></a>In the case of e2 studio
1. Create project from scratch
   * ```File``` -> ```New``` -> ```Project```
    * ```Wizard``` -> ```C/C++``` -> ```C/C++ Project``` -> ```Next```
        * ```All``` -> ```Renesas CC-RX C/C++ Executable Project```
            * Enter any name on ```Project name``` -> ```Next```
                *Select device in ```Device Settings``` -> ```Target device```
                * Select RTOS and version in ```Toolchain Settings``` -> ```RTOS```
                * ```Configuration``` -> Generate ```Hardware Debug  configuration``` ->Select emulator you use
                * Select other setting as you like -> ```Next```
                    * ```Use Smart Configurator```に<font color="Red">Check</font> -> ```Exit```
2. Double click ```[Project name].scfg``` of newly created project
    * SC is booted
### <a name="creation_sc_project_cs"></a>In the case of CS+
1. Create new project
   * ```File``` -> ```Create new project```
    * ```Wizard``` -> ```Microcontroller``` -> ```RX```
        * ```Microcontroller which is used``` -> Select device which is used
        * ```Project type``` -> ```Application (CC-RX)```
        * Enter any name in ```Project name``` -> ```Next```
        * Select other setting as you like -> ```Create```
2. Double click ```Smart Configurator (Design tool)``` of newly created project
    * SC is booted

## <a name="board_setting"></a>Set board
1. Press ```Board``` tab on the bottom of the SC screen
2. Select board you want to use from ```Board``` category （Read Board Configuration File(BDF) into project）
   * By reading BDF, "pin setting" on Smart Configurator is automated.
      * ★Future improvement★ The settings of component and clock will be fully automated.
   * If your intended board does not appear as option, BDF can be installed from ```Download board information```.
      * ★Future improvement★ BDF will be able to be selected and installed with project creation wizard.
   * <a href="../../images/044_e2_studio_sc.png" target="_blank"><img src="../../images/044_e2_studio_sc.png" width="480px" target="_blank"></a>

## <a name="clock_setting"></a>Set clock
* ★Future improvement★ In tandem with BDF The setting will be unnecessary in e2 studio 2020-xx (Future version) （necessary before e2 studio 2020-07）
1. Press ```Clock```tab on the bottom of SC
2. By changing the values of check box and pulldown menu, perform clock setting
  * <a href="../../images/022_e2_studio_sc1.png" target="_blank"><img src="../../images/022_e2_studio_sc1.png" width="480px" target="_blank"></a>
3. Check build error（Not required but recommended）
   1.  Execute [Generate code](#code_generation) temporarily, and skeleton program according to the content which is set with SC is outputted.
   2.  Execute the build of project, and check that an error is not displayed on the console.
          In the case of * e2 studio ,execute ```Project``` -> ```Build all``` on the top screen of e2 studio to build.


## <a name="component_import"></a>Embed component
### <a name="add_component"></a>Add component
1. Press ```Component```tab on the bottom of SC screen
2. Press ```Add component``` in ```Component``` pane on the left of SC screen
3. Select component （FIT or CG）you want to add in the added window<br>（Can select several components by clicking while pressing Ctrl key）
4. Check that the component which you added in the above step is displayed on ```Component``` pane on the left of SC screen.
* <a href="../../images/069_setting_component.png" target="_blank"><img src="../../images/069_setting_component.png" width="480px" target="_blank"></a>
#### <a name="recovery_for_missing_fit"></a>How to solve the situation when your intended FIT module is not displayed
 * Select ```basic setting``` in ```Select software component``` window, and check ```Display all FIT modules```
 * If your intended FIT module is not displayed by following the above step, check if the module exists in [Save destination folder of FIT module](https://github.com/renesas/rx72n-envision-kit/wiki/How-to-use-the-Smart-Configurator#save-destination-folder-of-fit-module)or not.
     1. Access [Save destination folder of FIT module](https://github.com/renesas/rx72n-envision-kit/wiki/How-to-use-the-Smart-Configurator#save-destination-folder-of-fit-module)
     2. Check that the intended FIT module exists in this file path        
     3. If it exists, reboot IDE, while SC is closed, and check again if your intended module exists or not.
     4. If it does not exist, [import FIT module manually](#fit_import_manually)
#### <a name="fit_import_manually"></a>How to import FIT module manually
Official document：[Firmware Integration Technology (FIT)](https://www.renesas.com/us/en/software-tool/fit) -> [RX Family Manually Importing Firmware Integration Technology Modules](https://www.renesas.com/us/en/document/apn/rx-family-manually-importing-firmware-integration-technology-modules?language=en&r=485911)
1. [Obtain](#rdp) your intended FIT module from [RX Driver Package (RDP)](https://www.renesas.com/products/software-tools/software-os-middleware-driver/software-package/rx-driver-package.html)
2. Copy the FIT module obtained in the above step to [Save destination folder of FIT module](https://github.com/renesas/rx72n-envision-kit/wiki/How-to-use-the-Smart-Configurator#save-destination-folder-of-fit-module).
3. After closing SC, boot IDE and check again if your intended module is displayed or not. 
#### <a name="stored_fit_folder"></a>Save destination folder of FIT module
* FIT module displayed in component adding operation refers to the following folder (Save destination folder of FIT module)
  * The file path which is set in ```Add component``` -> ```Basic setting``` -> ```Module Download``` -> ```Location (RX)```
    * Default of e2 studio：``` C:\Users\[User name]\.eclipse\org.eclipse.platform_download\FITModules```
  * One FIT module consists of the following files（x: Function name, n: version）
    * ```r_xxx_vn.nn.zip```：Module itself in which source code and documents are compressed.
    * ```r_xxx_vn.nn.xml```：Module information file necessary to SC liaison
    * ```r_xxx_vn.nn.mdf```：Definition file which is used for SC component setting（Only some FIT modules）
    * ```r_xxx_vn.nn_extend.mdf```：Definition file which is used for SC component setting（Only some FIT modules）
* Right after manually adding FIT module, it is not recognized by Smart Configurator.
  *  **Reboot e2 studio or CS+** temporarily
#### <a name="rdp"></a>RX Driver Package (RDP)
* [RX Driver Package (RDP)](https://www.renesas.com/products/software-tools/software-os-middleware-driver/software-package/rx-driver-package.html) is a free package including BSP for RX MCUs, driver and middleware.
* The above software is provided as [FIT module](https://www.renesas.com/products/software-tools/software-os-middleware-driver/software-package/fit.html).
* The version of included FIT module varies with that of RDP.
  * By clicking ```previous version information``` of  [bottom of the page](https://www.renesas.com/products/software-tools/software-os-middleware-driver/software-package/rx-driver-package.html), you can refer to a link destination of the previous versions of RDP.
  * To have Smart Configurator recognize the FIT module included in the previous RDP versions, you need to operate manually ⇒ [Save destination folder of #FIT module ](Save destination folder of #FIT module)
* You can download RDP from SC（Note: only the latest version）
  1. ```Add component``` -> ```Download other software```
  2. When region selection window is displayed, select the region you live in such as ```Japan``` -> ```OK```
  3. Select RDP -> Specify ```Module folder―・Path``` as an option -> ```Download``` -> ```Agree```
      *  The FIT module included in RDP is automatically expanded in ```Module folder―・Path```
      *  <a href="../../images/082_rdp_download.png" target="_blank"><img src="../../images/082_rdp_download.png" width="480px" target="_blank"></a>
* **For the MCUs before RX64M model such as RX63N, use FIT module with RDP V1.19**
  * These MCUs do not support the latest FIT module.

### <a name="component_setting"></a>Set component
1. Press  ```Component```tab on the bottom of SC screen
2. Select a component you want to set in ```Component```pane on the left of SC screen.
3. Change the setting in ```setting``` pane on the center of SC screen.
     * <a href="../../images/070_setting_sdhi1.png" target="_blank"><img src="../../images/070_setting_sdhi1.png" width="480px" target="_blank"></a>

### <a name="change_component_version"></a>Change the version of component
* Execute according to the situation
1. Press ```Component``` tab on the bottom of SC screen
2. Right-click a component of which you want to change the version in ```component``` pane on the left of SC screen.
3. Press ```Change version``` in the context menu which is displayed
4. In the displayed window、Specify the version of the change destination```Version after the change``` -> ```Next```
5. Check setting items which are changed in the screen of changed setting which will be displayed next. -> If there is no problem,```Exit```
6. [Generate code](#code_generation) is automatically executed, and component version is changed.
7. Right-click the component of which version was changed in ```Component``` pane on the left of SC screen. -> Press ```Change version``` and check that the version has been automatically changed.

### <a name="delete_component"></a>Delete component
* Execute according to the situation
1. Press ```Component``` tab on the bottom of SC screen
2. Select a component you want to delete in ```Component```pane on the left of SC screen
3. Press ```Delete component``` in ```Component``` pane on the left of SC screen
4. Press ```Yes``` in the displayed window for checking.
5. Check that your intended component is deleted in ```Component``` pane on the left of SC screen.

## <a name="pin_setting"></a>Pin setting
1. Press ```Pin``` tab on the bottom of SC screen
2. Select the resource of a pin you want to set in```Hardware resource``` pane on the left of SC screen.
3. Check the box of  ```Use``` in ```Pin function``` pane on the center of SC screen to select pins which you want to use.
4. Change pulldown menu of ```Pin assignment``` in ```Pin function``` pane on the center of SC screen to set the port number of a pin you want to use.
   * Customize the number of pins and ports which you use, by referring to the circuit diagram.
   * <a href="../../images/074_setting_pin_sdhi.png" target="_blank"><img src="../../images/074_setting_pin_sdhi.png" width="480px" target="_blank"></a>

## <a name="interrupt_setting"></a>Set interrupt
* [Note] not linked with FIT interrupt setting
1. Press ```Interrupt```tab on the bottom of SC screen
2. Select an interrupt you want to use to set the function of  ```Interrupt``` and ```priority level```.
3. Select an interrupt you want to use and press ```Move upward``` and ```Move downward``` to change vector number


## <a name="code_generation"></a>Generate code
1. Press ```Generate code```button on the upper right of SC screen.
     * <a href="../../images/081_code_generate.png" target="_blank"><img src="../../images/081_code_generate.png" width="480px" target="_blank"></a>
2. Program code according to the content which is set on SC is automatically generated.
3. Execute build of the project and check that an error is not displayed on the console.
     In the case of * e2 studio, execute ```Project``` -> ```Build all``` on the top of e2 studio screen to build.
* The source code subject of SC control （Source program under .\src\smc_gen\） right before source generation is backed up in .\trash\folder right after executing source generation.