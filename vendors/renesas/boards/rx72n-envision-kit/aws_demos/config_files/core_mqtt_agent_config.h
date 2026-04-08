/*
 * coreMQTT Agent configuration for RX72N Envision Kit.
 * Derived from iot-reference-rx 202406.04-LTS-rx-1.2.0 and kept in the
 * current board-local config_files path during the first middleware refresh pass.
 */

#ifndef CORE_MQTT_AGENT_CONFIG_H_
#define CORE_MQTT_AGENT_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

#include "logging_levels.h"

#ifndef LIBRARY_LOG_NAME
#define LIBRARY_LOG_NAME    "MQTT_Agent"
#endif

#ifndef LIBRARY_LOG_LEVEL
#define LIBRARY_LOG_LEVEL    LOG_INFO
#endif

#include "logging_stack.h"

/* Keep the agent responsive while still letting it process incoming traffic. */
#define MQTT_AGENT_MAX_EVENT_QUEUE_WAIT_TIME    ( 50U )

#ifdef __cplusplus
}
#endif

#endif /* CORE_MQTT_AGENT_CONFIG_H_ */
