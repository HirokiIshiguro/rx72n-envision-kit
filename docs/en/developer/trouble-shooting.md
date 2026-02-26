# Can import project but can not execute build
## Cause
* The compiler version (V301) which was used in the imported project does not correspond to the compiler version (V302 or later) which is installed by the user.

## Countermeasure 1
* Open the property of the project "aws_demos" on e2 studio
* Select "C/C++Build">"Setting">"Toolchain" tab, and select "Version">"v3.02.00" (If it is blank)
* Select "C/C++Build">"Setting">"Tool setting" tab, and select"Compiler">"Source"
* Double-click "implicitlyinclude.h" inside "the file which is included at the head of the compilation unit".
* When "Edit file/path" window opens, click "File/system", and select "implicitlyinclude.h" of "${base_folder}/vendors/renesas/amazon_freertos_common/compiler_support/ccrx"
* Select "OK" and "Apply and Close" and close the window.

## Countermeasure 2
* Change the compiler version installed by the user to V301

# If user application is installed from bootloader, verification result will be NG.
## Cause
* Version of Tera Term is not appropriate
* The setting of Tera Term is insufficient.

## Countermeasure
* Double-check the following setting.
    * [Tera Term](https://osdn.net/projects/ttssh2/) 4.105 or later
        * Turn off [High-speed file transfer with serial connection](https://teratermproject.github.io/manual/5/en/setup/teraterm-trans.html#FileSendHighSpeedMode): FileSendHighSpeedMode=off 
            * Tera Term -> Setting -> Read setting -> Open TERATERM.INI with text editor -> Change setting -> Save -> Reboot Tera Term
