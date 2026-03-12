#!/usr/bin/env bash

set -euo pipefail

: "${DEVICE_SLOT:?DEVICE_SLOT is required}"

command_port_default="/dev/serial/by-id/usb-Renesas_Electronics_Corporation_Renesas_RSK_USB_Serial_Port_0000000000001-if00"

case "${DEVICE_SLOT}" in
  01)
    uart_port_default="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A904CXV7-if00-port0"
    mac_addr_default="76:90:50:00:79:01"
    ;;
  02)
    uart_port_default="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AV0KOEEG-if00-port0"
    mac_addr_default="76:90:50:00:79:02"
    ;;
  03)
    uart_port_default="/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_AV0KOE92-if00-port0"
    mac_addr_default="76:90:50:00:79:03"
    ;;
  *)
    echo "ERROR: Unsupported DEVICE_SLOT=${DEVICE_SLOT}" >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

export UART_PORT="${UART_PORT:-${uart_port_default}}"
export COMMAND_PORT="${COMMAND_PORT:-${command_port_default}}"
export MAC_ADDR="${MAC_ADDR:-${mac_addr_default}}"
