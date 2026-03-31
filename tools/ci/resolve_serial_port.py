#!/usr/bin/env python3
"""resolve_serial_port: Resolve serial port path for current platform.

On Windows, if a Linux-style path (/dev/serial/by-id/...) is provided,
attempt to find the matching Windows COM port by serial number.

Usage:
  python resolve_serial_port.py /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A904CXV7-if00-port0
  -> COM7

  python resolve_serial_port.py COM7
  -> COM7  (passthrough)
"""

import re
import sys


def resolve_port(port_path: str) -> str:
    """Resolve a serial port path for the current platform.

    If on Windows and given a Linux /dev/serial/by-id/ path, attempt to
    find the matching COM port by extracting the USB serial number.
    """
    if sys.platform != "win32":
        return port_path  # On Linux, keep as-is

    # If it's already a Windows COM port, return as-is
    if re.match(r'^COM\d+$', port_path, re.IGNORECASE):
        return port_path

    # Try to extract USB serial number from Linux path
    # Examples:
    #   /dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A904CXV7-if00-port0
    #   /dev/serial/by-id/usb-Renesas_Electronics_Corporation_Renesas_RSK_USB_Serial_Port_0000000000001-if00
    serial_match = None

    # Pattern 1: VID-specific serial like A904CXV7 (FTDI)
    m = re.search(r'usb-FTDI_[^-]*_([A-Za-z0-9]+)-if', port_path)
    if m:
        serial_match = m.group(1)

    # Pattern 2: Renesas serial like 0000000000001
    if not serial_match:
        m = re.search(r'_Port_([0-9]+)-if', port_path)
        if m:
            serial_match = m.group(1)

    # Pattern 3: Generic - take the last segment before -if
    if not serial_match:
        m = re.search(r'_([A-Za-z0-9]+)-if\d+', port_path)
        if m:
            serial_match = m.group(1)

    if serial_match:
        try:
            import serial.tools.list_ports
            for p in serial.tools.list_ports.comports():
                if serial_match in (p.serial_number or ''):
                    print(f"[resolve_serial_port] {port_path} -> {p.device} "
                          f"(matched serial={serial_match})", file=sys.stderr)
                    return p.device
                # Also check hwid for partial serial match
                if serial_match in (p.hwid or ''):
                    print(f"[resolve_serial_port] {port_path} -> {p.device} "
                          f"(matched hwid contains {serial_match})", file=sys.stderr)
                    return p.device
        except ImportError:
            print("[resolve_serial_port] WARNING: pyserial not available for COM port resolution",
                  file=sys.stderr)

    print(f"[resolve_serial_port] WARNING: Could not resolve {port_path} to a Windows COM port. "
          f"Passing through as-is.", file=sys.stderr)
    return port_path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port_path>", file=sys.stderr)
        sys.exit(1)
    print(resolve_port(sys.argv[1]))
