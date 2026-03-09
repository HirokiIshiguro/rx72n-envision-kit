#!/usr/bin/env python3
"""
Provision phase8b credentials to RX72N Envision Kit over the short-lived CLI.

This is the RX72N-specific variant of the iot-reference-rx provisioning flow.
The phase8b firmware exposes the FreeRTOS CLI for roughly 10 seconds after boot,
so CI should reset the device immediately before opening the command port.
"""

import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "provisioning"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "test_scripts"))

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

from provisioning.security import mask_sensitive_output
from device_config_loader import load_device_config, get_cert_env_var_name, get_key_env_var_name


DEFAULT_PORT = os.environ.get("COMMAND_PORT", "COM10")
DEFAULT_BAUD = int(os.environ.get("COMMAND_BAUD_RATE", "115200"))
DEFAULT_CHAR_DELAY = 0.002
DEFAULT_LINE_DELAY = 0.5
DEFAULT_BOOT_WAIT = 3.0
DEFAULT_CLI_TIMEOUT = 15.0


def send_chars(ser, text, char_delay):
    for ch in text:
        ser.write(ch.encode("ascii"))
        time.sleep(char_delay)


def send_command(ser, command, char_delay, line_delay, expect_ok=True):
    ser.reset_input_buffer()
    send_chars(ser, command, char_delay)
    ser.write(b"\r\n")
    time.sleep(line_delay)
    response = ser.read(ser.in_waiting or 1024).decode("ascii", errors="replace")

    if expect_ok and "Error" in response:
        print(f"  ERROR in response: {mask_sensitive_output(response.strip())}")
        return None

    return response


def send_pem_command(ser, key_name, pem_path, char_delay, line_delay):
    with open(pem_path, "r", encoding="utf-8") as f:
        pem_content = f.read()

    pem_content = pem_content.replace("\r\n", "\n").replace("\r", "\n").strip()
    total_len = len(f"conf set {key_name} ") + len(pem_content)
    if total_len > 4090:
        print(f"  WARNING: Command length ({total_len}) near buffer limit (4096)")

    print(f"  Sending: conf set {key_name} <{pem_path}> ({len(pem_content)} bytes)")
    send_chars(ser, f"conf set {key_name} ", char_delay)
    send_chars(ser, pem_content, char_delay)
    ser.write(b"\r\n")
    time.sleep(line_delay)
    response = ser.read(ser.in_waiting or 1024).decode("ascii", errors="replace")

    if "OK" in response:
        print("  OK")
        return True
    if "Error" in response:
        print(f"  ERROR: {mask_sensitive_output(response.strip())}")
        return False

    print(f"  Response: {mask_sensitive_output(response.strip())}")
    return True


def wait_for_boot(ser, timeout):
    print(f"Waiting for device boot ({timeout}s timeout)...")
    start = time.time()
    collected = ""
    while time.time() - start < timeout:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode("ascii", errors="replace")
            collected += data
            sys.stdout.write(mask_sensitive_output(data))
            sys.stdout.flush()
        time.sleep(0.1)
    return collected


def enter_cli_mode(ser, char_delay, line_delay, timeout):
    print("Entering CLI mode...")
    ser.reset_input_buffer()
    send_chars(ser, "CLI", char_delay)
    ser.write(b"\r\n")
    time.sleep(line_delay)

    start = time.time()
    collected = ""
    while time.time() - start < timeout:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting).decode("ascii", errors="replace")
            collected += data
            sys.stdout.write(mask_sensitive_output(data))
            sys.stdout.flush()
            if ">" in collected or "Going to FreeRTOS-CLI" in collected:
                print("\nCLI mode entered successfully")
                return True
        time.sleep(0.1)

    print("\nWARNING: CLI prompt not detected, continuing anyway...")
    return True


def resolve_device_args(args, parser):
    if args.device_id:
        device = load_device_config(args.device_id)
        print(f"Loaded config for device: {args.device_id}")

        if args.port == DEFAULT_PORT:
            args.port = device["command_port"]
        if args.baud == DEFAULT_BAUD:
            args.baud = device["command_baud"]
        if not args.endpoint:
            args.endpoint = device["aws_endpoint"]
        if not args.thing_name:
            args.thing_name = device["thing_name"]
        if not args.cert:
            cert_var = get_cert_env_var_name(args.device_id)
            args.cert = os.environ.get(cert_var)
            if not args.cert:
                parser.error(f"Environment variable {cert_var} not set")
            print(f"Certificate path from ${cert_var}")
        if not args.key:
            key_var = get_key_env_var_name(args.device_id)
            args.key = os.environ.get(key_var)
            if not args.key:
                parser.error(f"Environment variable {key_var} not set")
            print(f"Private key path from ${key_var}")
        if not args.codesigner_cert and device.get("codesigner_cert"):
            repo_root = os.path.dirname(os.path.dirname(__file__))
            candidate = os.path.join(repo_root, device["codesigner_cert"])
            if os.path.isfile(candidate):
                args.codesigner_cert = candidate
                print(f"Code signer cert from device_config: {candidate}")

    if not args.endpoint:
        parser.error("--endpoint is required (or use --device-id)")
    if not args.thing_name:
        parser.error("--thing-name is required (or use --device-id)")
    if not args.cert:
        parser.error("--cert is required (or use --device-id)")
    if not args.key:
        parser.error("--key is required (or use --device-id)")

    for path, desc in ((args.cert, "Certificate"), (args.key, "Private key")):
        if not os.path.isfile(path):
            parser.error(f"{desc} file not found: {path}")
    if args.codesigner_cert and not os.path.isfile(args.codesigner_cert):
        parser.error(f"Code signer certificate file not found: {args.codesigner_cert}")


def provision(args):
    print("=" * 60)
    print("phase8b Device Provisioning")
    print("=" * 60)
    print(f"Port:       {args.port}")
    print(f"Baud:       {args.baud}")
    print(f"Thing Name: {args.thing_name}")
    print(f"Endpoint:   {args.endpoint}")
    print(f"Cert:       {args.cert}")
    print(f"Key:        {args.key}")
    if args.codesigner_cert:
        print(f"Code Sign:  {args.codesigner_cert}")
    if args.reset_cmd:
        print(f"Reset cmd:  {args.reset_cmd}")
    print("=" * 60)

    if args.reset_cmd:
        print("Running external reset command before opening serial...")
        result = subprocess.run(args.reset_cmd, shell=True)
        if result.returncode != 0:
            print(f"ERROR: reset command failed with exit code {result.returncode}")
            return 1

    try:
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0,
        )
    except serial.SerialException as e:
        print(f"ERROR: Cannot open {args.port}: {e}")
        return 1

    print(f"Serial port {args.port} opened")

    try:
        if not args.skip_boot_wait:
            wait_for_boot(ser, args.boot_wait)

        if not enter_cli_mode(ser, args.char_delay, args.line_delay, args.cli_timeout):
            print("ERROR: Failed to enter CLI mode")
            return 1

        if args.format:
            print("\n--- Format data flash ---")
            resp = send_command(ser, "format", args.char_delay, args.line_delay * 2)
            if resp and "OK" in str(resp):
                print("  Format OK")
            else:
                print(f"  Format response: {mask_sensitive_output(str(resp).strip()) if resp else 'No response'}")

        print(f"\n--- Set thing name: {args.thing_name} ---")
        if send_command(ser, f"conf set thingname {args.thing_name}", args.char_delay, args.line_delay) is None:
            return 1

        print(f"\n--- Set endpoint: {args.endpoint} ---")
        if send_command(ser, f"conf set endpoint {args.endpoint}", args.char_delay, args.line_delay) is None:
            return 1

        print("\n--- Set device certificate ---")
        if not send_pem_command(ser, "cert", args.cert, args.char_delay, args.line_delay):
            return 1

        print("\n--- Set private key ---")
        if not send_pem_command(ser, "key", args.key, args.char_delay, args.line_delay):
            return 1

        if args.codesigner_cert:
            print("\n--- Set code signing certificate ---")
            if not send_pem_command(ser, "codesigncert", args.codesigner_cert, args.char_delay, args.line_delay):
                return 1
        else:
            print("\nWARNING: No code signing certificate provided; OTA signature verification will fail")

        print("\n--- Commit to data flash ---")
        resp = send_command(ser, "conf commit", args.char_delay, args.line_delay * 3)
        if resp is None:
            return 1
        print(f"  {mask_sensitive_output(resp.strip()) if resp else 'No response'}")

        if not args.no_reset:
            print("\n--- Reset device ---")
            send_command(ser, "reset", args.char_delay, args.line_delay, expect_ok=False)
            print("  Reset command sent")
            if not args.quiet:
                print("\n--- Device boot output ---")
                wait_for_boot(ser, 5.0)
    finally:
        ser.close()
        print(f"\nSerial port {args.port} closed")

    print("\n" + "=" * 60)
    print("PROVISIONING COMPLETE")
    print("=" * 60)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Provision AWS IoT credentials to phase8b RX72N via UART CLI"
    )
    parser.add_argument("--device-id", help="Device ID (loads config from device_config.json)")
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"Serial port (default: {DEFAULT_PORT})")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"Baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("--thing-name", help="AWS IoT Thing name")
    parser.add_argument("--endpoint", help="AWS IoT MQTT endpoint URL")
    parser.add_argument("--cert", help="Path to device certificate PEM file")
    parser.add_argument("--key", help="Path to device private key PEM file")
    parser.add_argument("--codesigner-cert", help="Path to OTA code signing certificate PEM file")
    parser.add_argument("--char-delay", type=float, default=DEFAULT_CHAR_DELAY,
                        help=f"Delay between characters in seconds (default: {DEFAULT_CHAR_DELAY})")
    parser.add_argument("--line-delay", type=float, default=DEFAULT_LINE_DELAY,
                        help=f"Delay after each command in seconds (default: {DEFAULT_LINE_DELAY})")
    parser.add_argument("--boot-wait", type=float, default=DEFAULT_BOOT_WAIT,
                        help=f"Seconds to wait for boot messages (default: {DEFAULT_BOOT_WAIT})")
    parser.add_argument("--cli-timeout", type=float, default=DEFAULT_CLI_TIMEOUT,
                        help=f"Seconds to wait for CLI prompt (default: {DEFAULT_CLI_TIMEOUT})")
    parser.add_argument("--reset-cmd", help="External reset/run command executed before opening UART")
    parser.add_argument("--format", action="store_true", help="Format data flash before provisioning")
    parser.add_argument("--no-reset", action="store_true", help="Do not reset device after provisioning")
    parser.add_argument("--skip-boot-wait", action="store_true",
                        help="Skip waiting for boot messages (device already in CLI mode)")
    parser.add_argument("--quiet", action="store_true", help="Suppress boot output after reset")
    args = parser.parse_args()

    resolve_device_args(args, parser)
    return provision(args)


if __name__ == "__main__":
    sys.exit(main())
