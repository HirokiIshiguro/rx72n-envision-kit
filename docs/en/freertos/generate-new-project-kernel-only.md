# Things to prepare
* Indispensable
    * RX72N Envision Kit × 1 unit
    * USB cable (USB Micro-B --- USB Type A) × 1 
    * Windows PC × 1 unit
        * Tools to be installed in Windows PC 
            * [e2 studio 2020-10](https://www.renesas.com/products/software-tools/tools/ide/e2studio.html)
            * [CC-RX](https://www.renesas.com/products/software-tools/tools/compiler-assembler/compiler-package-for-rx-family.html) V3.02以降

# Boot e2 studio to generate new project
* File -> New -> Project
    * Wizard -> C/C++ -> C/C++ Project -> Next
        * All -> Renesas CC-RX C/C++ Executable Projecta
            * Project name = Input rx72n_envision_kit  -> Next
                * Toolchain Settings
                    * RTOS -> FreeRTOS(Kernel Only)
                    * If nothing is displayed in RTOS Version, obtain RTOS package form "Manage RTOS Versions..." link
                * Device Settings 
                    * Target Board -> EnvisionRX72N
                        * When EnvisionRX72N can be selected：Target device is automatically selected.
                        * When EnvisionRX72N can not be selected：Target device is not automatically selected
                            * In this case, select Download Additional Boards to download EnvisionRX72N
                            * Enable to install BDF during new project generation, too.
                * Configuration -> Generate Hardware Debug configuration -> E2 Lite (RX) -> Next
                    * Check "use Smart Configurator" -> Exit

# Perform setting with Smart Configurator
* [Set clock](https://github.com/renesas/rx72n-envision-kit/wiki/How-to-use-the-Smart-Configurator#set-clock)

# By using FreeRTOS task and generating 0.1 second cycle interrupt, turn on and off the LED in 0.1 second cycle.
## Register task with Smart Configurator to generate code.
* <a href="../../images/056_e2_studio_sc.png" target="_blank"><img src="../../images/056_e2_studio_sc.png" width="480px" target="_blank"></a>
    * Press "component" tab on the lower part of Smart Configurator screen
    * Select FreeRTOS_Object -> Task
    * Enter led_task on Task Code and Task Name
    * Generate code

## After 0.1 second waiting state, add code to turn on and off LED in LED task (led_task.c)
* Use a function called vTaskDelay() which creates waiting state.
    * An argument is waiting time of which resolution is TimeTick=1ms of FreeRTOS
    * By specifying 100, you can create 100ms or 0.1 second waiting state.

```led_task.c
#include "task_function.h"
/* Start user code for import. Do not edit comment generated here */
#include "platform.h"
/* End user code. Do not edit comment generated here */

void led_task(void * pvParameters)
{
/* Start user code for function. Do not edit comment generated here */
	PORT4.PDR.BYTE = 1;	/* Originally should be set with Smart Configurator (★Require improvement) */
	while(1)
	{
		vTaskDelay(100);
		if(PORT4.PIDR.BIT.B0 == 1)
		{
			PORT4.PODR.BIT.B0 = 0;
		}
		else
		{
			PORT4.PODR.BIT.B0 = 1;
		}
	}
/* End user code. Do not edit comment generated here */
}
/* Start user code for other. Do not edit comment generated here */
/* End user code. Do not edit comment generated here */
```

## Create waiting state to pass control to OS during infinite loop in main task (rx72n_envision_kit.c)
* Main task is registered with priority "3"
*  LED task is registered with priority"1" 
* The larger number has higher priority 
* Since program counter is not passed to LED task in this state, LED control does not operate.
* Accordingly, creates waiting state to pass control to OS during infinite loop as shown below.

```rx72n_envision_kit.c
#include "FreeRTOS.h"
#include "task.h"

void main_task(void *pvParameters)
{

	/* Create all other application tasks here */

	while(1)
	{
		vTaskDelay(10);
	}

	vTaskDelete(NULL);

}
```

### Reference
* What would happen when the priority is the same among multiple tasks?
    * FreeRTOS has a configuration to select the mechanism of scheduler. 
    * Dfault is  "Preemptive" valid.
    * In this case, in the case where a task with the same priority exists, when TimeTick=1ms of FreeRTOS passes or a task under execution ends, shifts to another task with the same priority.

## Adjust heap capacity
* If increases resources such as task, necessary heap memory also increases.
* FreeRTOS can set heap memory
    * Firstly, check an estimated value of heap calculated by Smart Configurator.
        * <a href="../../images/057_e2_studio_sc.png" target="_blank"><img src="../../images/057_e2_studio_sc.png" width="480px" target="_blank"></a>
        * Estimated at 5856byte(s) for Total For Heap Usage
    * Next, set the heap value of FreeRTOS with Smart Configurator
        * <a href="../../images/058_e2_studio_sc.png" target="_blank"><img src="../../images/058_e2_studio_sc.png" width="480px" target="_blank"></a>
        * Enter a value with some room for an estimated value. In this example enter 8 (8KB setting value)
        * If executes with insufficient heap, infinite loop occurs with vApplicationMallocFailedHook()
# Debugger setting
* [Reference](https://github.com/renesas/rx72n-envision-kit/wiki/Generate-new-project-%28bare-metal%29#debugger-setting)

# Check operation
* [Reference](https://github.com/renesas/rx72n-envision-kit/wiki/Generate-new-project-%28bare-metal%29#check-operation)
