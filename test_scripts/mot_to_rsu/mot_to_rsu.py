#!/usr/bin/env python3
"""
mot_to_rsu.py - Motorola S-record (.mot) to Renesas Secure Update (.rsu) converter

Converts aws_demos.mot (or other user program .mot files) into .rsu format
for UART download via the RX72N secure boot loader.

This is a Python CUI replacement for the C# "Renesas Secure Flash Programmer"
tool's Update mode. The C# tool's CUI Update mode had a bug where the
private key path was not passed for sig-sha256-ecdsa verification type.

Supported features:
    - Motorola S-record parsing (S0, S1, S2, S3 records)
    - sig-sha256-ecdsa signing (ECDSA P-256, SHA-256, RFC 6979 deterministic k)
    - RX72N 4MB dual-bank secure bootloader address map
    - Existing .rsu file verification

Usage:
    # Convert .mot to .rsu
    python mot_to_rsu.py --mot aws_demos.mot --key secp256r1.privatekey -o userprog.rsu

    # With custom sequence number
    python mot_to_rsu.py --mot aws_demos.mot --key secp256r1.privatekey -o userprog.rsu --seq-no 2

    # Verify existing .rsu file
    python mot_to_rsu.py --verify userprog.rsu --key secp256r1.privatekey

Dependencies:
    pip install cryptography

Reference:
    - C# source: vendors/renesas/tools/mot_file_converter/Renesas Secure Flash Programmer/FormMain.cs
    - RSU format: https://docs.aws.amazon.com/ja_jp/freertos/latest/userguide/microchip-bootloader.html
"""

import argparse
import struct
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils
except ImportError:
    print("ERROR: 'cryptography' package is required.")
    print("       Install with: pip install cryptography")
    sys.exit(1)


# ==============================================================================
# MCU Address Map definitions
# Corresponds to FormMain.cs McuSpecs dictionary
# ==============================================================================

MCU_SPECS = {
    "RX72N": {
        "name": "RX72N(ROM 4MB)/Secure Bootloader=256KB",
        "hardware_id": 0x00000009,
        "user_program_top_address": 0xFFE00300,
        "user_program_bottom_address": 0xFFFBFFFF,
        "user_program_mirror_top_address": 0xFFC00300,
        "user_program_mirror_bottom_address": 0xFFDBFFFF,
        "bootloader_top_address": 0xFFFC0000,
        "bootloader_bottom_address": 0xFFFFFFFF,
        "code_flash_top_address": 0xFFC00000,
        "code_flash_bottom_address": 0xFFFFFFFF,
        "bootloader_const_data_top_address": 0x00100000,
        "bootloader_const_data_bottom_address": 0x001007FF,
        "user_program_const_data_top_address": 0x00100800,
        "user_program_const_data_bottom_address": 0x001077FF,
        "data_flash_top_address": 0x00100000,
        "data_flash_bottom_address": 0x00107FFF,
    },
}


# RSU format constants (from FormMain.cs)
RSU_HEADER_SIZE = 0x200       # 512 bytes
RSU_DESCRIPTOR_SIZE = 0x100   # 256 bytes
RSU_APP_OFFSET = 0x300        # Application binary starts here

IMAGE_FLAG_BLANK = 0xFF
IMAGE_FLAG_TESTING = 0xFE
IMAGE_FLAG_VALID = 0xFC
IMAGE_FLAG_INVALID = 0xF8

SIG_TYPE_SHA256_ECDSA = "sig-sha256-ecdsa"
ECDSA_P256_SIG_SIZE = 64      # r(32) + s(32) for secp256r1


# ==============================================================================
# Motorola S-record parser
# ==============================================================================

def parse_mot_file(mot_path, mcu_spec):
    """
    Parse a Motorola S-record (.mot) file into code flash and data flash images.

    The .mot file contains S-records with addresses in the MCU's memory map.
    Code flash data is extracted at offset = (address - user_program_top_address).
    Data flash data is extracted at offset = (address - user_program_const_data_top_address).

    Args:
        mot_path: Path to .mot file
        mcu_spec: MCU address map dictionary

    Returns:
        (code_flash_image, data_flash_image) - bytearray images initialized to 0xFF
    """
    user_prog_top = mcu_spec["user_program_top_address"]
    user_prog_bottom = mcu_spec["user_program_bottom_address"]
    code_flash_top = mcu_spec["code_flash_top_address"]
    code_flash_bottom = mcu_spec["code_flash_bottom_address"]
    const_data_top = mcu_spec["user_program_const_data_top_address"]
    const_data_bottom = mcu_spec["user_program_const_data_bottom_address"]
    data_flash_top = mcu_spec["data_flash_top_address"]
    data_flash_bottom = mcu_spec["data_flash_bottom_address"]

    user_prog_size = user_prog_bottom - user_prog_top + 1
    const_data_size = const_data_bottom - const_data_top + 1

    # Initialize images to 0xFF (erased flash state)
    code_flash_image = bytearray(b'\xff' * user_prog_size)
    data_flash_image = bytearray(b'\xff' * const_data_size)

    code_bytes_written = 0
    data_bytes_written = 0
    warnings = []

    with open(mot_path, 'r') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            rec_type = line[0:2]

            # Determine address length based on record type
            if rec_type == "S0":
                continue  # Header record - skip
            elif rec_type == "S1":
                addr_bytes = 2   # 16-bit address
            elif rec_type == "S2":
                addr_bytes = 3   # 24-bit address
            elif rec_type == "S3":
                addr_bytes = 4   # 32-bit address
            elif rec_type in ("S4", "S5", "S6", "S7", "S8", "S9"):
                continue  # Termination / count records - skip
            else:
                continue

            # Parse byte count, address, and data
            byte_count = int(line[2:4], 16)
            data_len = byte_count - addr_bytes - 1  # subtract address and checksum

            addr_hex = line[4:4 + addr_bytes * 2]
            address = int(addr_hex, 16)

            data_start = 4 + addr_bytes * 2
            data_hex = line[data_start:data_start + data_len * 2]
            data_bytes = bytes.fromhex(data_hex)

            # Route to data flash or code flash image
            if data_flash_top <= address <= data_flash_bottom:
                # Data flash region
                if address < const_data_top or address > const_data_bottom:
                    warnings.append(
                        f"line {line_no}: address 0x{address:08x} in data flash "
                        f"but outside user const data range "
                        f"0x{const_data_top:08x}-0x{const_data_bottom:08x}"
                    )
                    continue
                offset = address - const_data_top
                data_flash_image[offset:offset + len(data_bytes)] = data_bytes
                data_bytes_written += len(data_bytes)

            elif code_flash_top <= address <= code_flash_bottom:
                # Code flash region
                if address < user_prog_top or address > user_prog_bottom + 1:
                    warnings.append(
                        f"line {line_no}: address 0x{address:08x} in code flash "
                        f"but outside user program range "
                        f"0x{user_prog_top:08x}-0x{user_prog_bottom:08x}"
                    )
                    continue
                offset = address - user_prog_top
                code_flash_image[offset:offset + len(data_bytes)] = data_bytes
                code_bytes_written += len(data_bytes)

    # Print warnings (limit to first 5)
    for w in warnings[:5]:
        print(f"  WARNING: {w}")
    if len(warnings) > 5:
        print(f"  ... and {len(warnings) - 5} more warnings")

    print(f"  Code flash: {code_bytes_written:,} bytes written")
    print(f"  Data flash: {data_bytes_written:,} bytes written")
    print(f"  Image size: code={user_prog_size:,} bytes ({user_prog_size/1024:.0f} KB), "
          f"data={const_data_size:,} bytes ({const_data_size/1024:.0f} KB)")

    return code_flash_image, data_flash_image


# ==============================================================================
# ECDSA signing (sig-sha256-ecdsa)
#
# Corresponds to FormMain.cs Sign() and Verify() methods.
# Uses deterministic k per RFC 6979 (BouncyCastle HMacDsaKCalculator in C#,
# default behavior in Python cryptography library).
# ==============================================================================

def sign_ecdsa(data, key_path):
    """
    Sign data with ECDSA P-256 / SHA-256 (deterministic k per RFC 6979).

    The C# original:
        1. SHA256 hash of data
        2. ECDSA sign hash with deterministic k
        3. Return r || s (raw bytes, leading zeros stripped)

    This Python implementation:
        1. ECDSA sign with SHA-256 (library handles hashing)
        2. Decode DER to (r, s) integers
        3. Encode as r || s, each zero-padded to 32 bytes

    Note: The C# Sign() strips leading zeros from r and s, which can produce
    signatures shorter than 64 bytes. The C# Verify() assumes r is exactly
    32 bytes (Take(32)). This is a subtle bug in the C# code that only manifests
    when r or s < 2^248 (probability ~1/256 per component). This Python
    implementation always pads to 32 bytes, which is the correct behavior.

    Args:
        data: bytes to sign (descriptor + code flash image)
        key_path: path to PEM EC private key file

    Returns:
        signature: r || s raw bytes (64 bytes for P-256)
    """
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    # Sign with ECDSA SHA-256
    der_signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    # Decode DER to (r, s) integers
    r, s = utils.decode_dss_signature(der_signature)

    # Encode as raw r || s, each padded to 32 bytes (P-256)
    signature = r.to_bytes(32, byteorder='big') + s.to_bytes(32, byteorder='big')

    return signature


def verify_ecdsa(data, signature, key_path):
    """
    Verify ECDSA P-256 / SHA-256 signature.

    Args:
        data: bytes that were signed
        signature: r || s raw bytes (64 bytes)
        key_path: path to PEM EC private key file (public key extracted from it)

    Returns:
        True if valid, False otherwise
    """
    with open(key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    public_key = private_key.public_key()

    # Decode raw r || s to DER format
    r = int.from_bytes(signature[:32], byteorder='big')
    s = int.from_bytes(signature[32:64], byteorder='big')
    der_signature = utils.encode_dss_signature(r, s)

    try:
        public_key.verify(der_signature, data, ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


# ==============================================================================
# RSU file generation
# ==============================================================================

def build_rsu(code_flash_image, data_flash_image, mcu_spec, key_path, seq_no):
    """
    Build .rsu binary data from code/data flash images.

    RSU file layout (from FormMain.cs rsu_header class):
        0x000-0x006  Magic Code           "Renesas"    (7 bytes)
        0x007        Image Flag           0xfe=TESTING (1 byte)
        0x008-0x027  Signature Type       ASCII+pad    (32 bytes)
        0x028-0x02B  Signature Size       uint32 LE    (4 bytes)
        0x02C-0x12B  Signature            raw bytes    (256 bytes)
        0x12C-0x12F  Dataflash Flag       uint32 LE    (4 bytes)
        0x130-0x133  Dataflash Start Addr uint32 LE    (4 bytes)
        0x134-0x137  Dataflash End Addr   uint32 LE    (4 bytes)
        0x138-0x1FF  Reserved             zero         (200 bytes)
        --- Descriptor (signed area) ---
        0x200-0x203  Sequence Number      uint32 LE    (4 bytes)
        0x204-0x207  Start Address        uint32 LE    (4 bytes)
        0x208-0x20B  End Address          uint32 LE    (4 bytes)
        0x20C-0x20F  Execution Address    uint32 LE    (4 bytes)
        0x210-0x213  Hardware ID          uint32 LE    (4 bytes)
        0x214-0x2FF  Reserved             zero         (236 bytes)
        --- Application Binary ---
        0x300-...    Code flash image     binary       (N bytes)
        --- Data Flash (const data) ---
        ...          Data flash image     binary       (M bytes)

    Data flash (const data) is appended after code flash.
    The boot loader reads code flash first, performs integrity check,
    then reads data flash from UART (BOOT_LOADER_STATE_INSTALL_DATA_FLASH_READ_WAIT).

    Args:
        code_flash_image: bytearray of code flash data
        data_flash_image: bytearray of data flash data (user const data area)
        mcu_spec: MCU address map dictionary
        key_path: Path to EC private key PEM file
        seq_no: Sequence number (1-4294967295)

    Returns:
        bytes: complete .rsu file content
    """
    user_prog_top = mcu_spec["user_program_top_address"]
    user_prog_bottom = mcu_spec["user_program_bottom_address"]
    user_prog_size = user_prog_bottom - user_prog_top + 1
    hw_id = mcu_spec["hardware_id"]
    const_data_top = mcu_spec["user_program_const_data_top_address"]
    const_data_bottom = mcu_spec["user_program_const_data_bottom_address"]
    exec_addr = user_prog_bottom - 3  # execution_address = end_address - 3

    # --- Build descriptor (256 bytes) ---
    # Layout: seq_no(4) + start(4) + end(4) + exec(4) + hw_id(4) + reserved(236) = 256
    descriptor = bytearray(RSU_DESCRIPTOR_SIZE)
    struct.pack_into('<I', descriptor, 0, seq_no)
    struct.pack_into('<I', descriptor, 4, user_prog_top)
    struct.pack_into('<I', descriptor, 8, user_prog_bottom)
    struct.pack_into('<I', descriptor, 12, exec_addr)
    struct.pack_into('<I', descriptor, 16, hw_id)
    # reserved2 (236 bytes) already zeroed

    # --- Build data to sign: descriptor (256B) + code flash (user_prog_size B) ---
    signed_data = bytes(descriptor) + bytes(code_flash_image[:user_prog_size])

    print(f"\nSigning {len(signed_data):,} bytes "
          f"(descriptor={RSU_DESCRIPTOR_SIZE}, code={user_prog_size:,})...")

    # --- ECDSA sign ---
    signature = sign_ecdsa(signed_data, key_path)
    r_hex = signature[:32].hex()
    s_hex = signature[32:].hex()
    print(f"  r = {r_hex[:32]}...{r_hex[-8:]}")
    print(f"  s = {s_hex[:32]}...{s_hex[-8:]}")

    # --- Verify signature ---
    if not verify_ecdsa(signed_data, signature, key_path):
        print("ERROR: Signature self-verification failed!")
        sys.exit(1)
    print("  Verification: PASS")

    # --- Assemble RSU file ---
    rsu = bytearray()

    # Header (512 bytes total)
    rsu += b"Renesas"                                           # 0x000: Magic (7B)
    rsu += struct.pack('B', IMAGE_FLAG_TESTING)                 # 0x007: Image flag (1B)

    sig_type_bytes = SIG_TYPE_SHA256_ECDSA.encode('ascii')
    rsu += sig_type_bytes + b'\x00' * (32 - len(sig_type_bytes))  # 0x008: Sig type (32B)

    rsu += struct.pack('<I', len(signature))                    # 0x028: Sig size (4B)
    rsu += signature + b'\x00' * (256 - len(signature))         # 0x02C: Signature (256B)

    rsu += struct.pack('<I', 1)                                 # 0x12C: DF flag (4B)
    rsu += struct.pack('<I', const_data_top)                    # 0x130: DF start (4B)
    rsu += struct.pack('<I', const_data_bottom)                 # 0x134: DF end (4B)
    rsu += b'\x00' * 200                                        # 0x138: Reserved1 (200B)

    assert len(rsu) == RSU_HEADER_SIZE, \
        f"Header size mismatch: {len(rsu)} != {RSU_HEADER_SIZE}"

    # Descriptor (256 bytes)
    rsu += descriptor

    assert len(rsu) == RSU_APP_OFFSET, \
        f"Header+descriptor size mismatch: {len(rsu)} != {RSU_APP_OFFSET}"

    # Application binary (code flash, user_prog_size bytes)
    rsu += code_flash_image[:user_prog_size]

    # Data flash (const data, appended after code flash)
    # The boot loader reads this after code flash integrity check passes.
    # It transitions to BOOT_LOADER_STATE_INSTALL_DATA_FLASH_READ_WAIT
    # and calls const_data_block_read() which requires SCI buffer to be FULL.
    # SCI buffer size = FLASH_CF_MEDIUM_BLOCK_SIZE = 32KB.
    # User const data = 28KB (0x00100800-0x001077FF).
    # Must pad to 32KB to fill SCI buffer and trigger buffer_full_flag.
    FLASH_CF_MEDIUM_BLOCK_SIZE = 32768  # Must match boot_loader's SCI buffer size
    const_data_size = const_data_bottom - const_data_top + 1  # 28KB
    data_flash_block = bytearray(b'\xff' * FLASH_CF_MEDIUM_BLOCK_SIZE)  # 32KB, init 0xFF
    data_flash_block[:const_data_size] = data_flash_image[:const_data_size]
    rsu += data_flash_block

    expected_size = RSU_HEADER_SIZE + RSU_DESCRIPTOR_SIZE + user_prog_size + FLASH_CF_MEDIUM_BLOCK_SIZE
    assert len(rsu) == expected_size, \
        f"Total size mismatch: {len(rsu)} != {expected_size}"

    return bytes(rsu)


# ==============================================================================
# RSU verification
# ==============================================================================

def verify_rsu(rsu_path, key_path, mcu_spec, diag=False):
    """
    Verify an existing .rsu file's header and signature.

    Args:
        rsu_path: Path to .rsu file
        key_path: Path to EC private key PEM file
        mcu_spec: MCU address map dictionary
        diag: Print additional diagnostic info

    Returns:
        0 on success, 1 on failure
    """
    print(f"=== Verifying RSU file ===")
    print(f"  File: {rsu_path}")
    print(f"  Key:  {key_path}")
    print()

    with open(rsu_path, 'rb') as f:
        data = f.read()

    if len(data) < RSU_APP_OFFSET:
        print(f"ERROR: File too small ({len(data)} bytes, minimum {RSU_APP_OFFSET})")
        return 1

    # Parse header
    magic = data[0:7]
    image_flag = data[7]
    sig_type = data[8:40].rstrip(b'\x00').decode('ascii', errors='replace')
    sig_size = struct.unpack_from('<I', data, 0x28)[0]
    signature = data[0x2C:0x2C + sig_size]
    df_flag = struct.unpack_from('<I', data, 0x12C)[0]
    df_start = struct.unpack_from('<I', data, 0x130)[0]
    df_end = struct.unpack_from('<I', data, 0x134)[0]

    # Parse descriptor
    seq_no = struct.unpack_from('<I', data, 0x200)[0]
    start_addr = struct.unpack_from('<I', data, 0x204)[0]
    end_addr = struct.unpack_from('<I', data, 0x208)[0]
    exec_addr = struct.unpack_from('<I', data, 0x20C)[0]
    hw_id = struct.unpack_from('<I', data, 0x210)[0]

    image_flag_names = {
        0xFF: "BLANK", 0xFE: "TESTING", 0xFC: "VALID", 0xF8: "INVALID"
    }

    print(f"--- Header ---")
    print(f"  Magic:     {magic}")
    print(f"  ImageFlag: 0x{image_flag:02x} ({image_flag_names.get(image_flag, 'UNKNOWN')})")
    print(f"  SigType:   {sig_type}")
    print(f"  SigSize:   {sig_size} bytes")
    print(f"  DF Flag:   {df_flag}")
    print(f"  DF Start:  0x{df_start:08x}")
    print(f"  DF End:    0x{df_end:08x}")
    print()
    print(f"--- Descriptor ---")
    print(f"  SeqNo:     {seq_no}")
    print(f"  StartAddr: 0x{start_addr:08x}")
    print(f"  EndAddr:   0x{end_addr:08x}")
    print(f"  ExecAddr:  0x{exec_addr:08x}")
    print(f"  HW_ID:     0x{hw_id:08x}")
    print()
    print(f"--- File ---")
    print(f"  Size:      {len(data):,} bytes ({len(data)/1024:.1f} KB)")

    payload_size = len(data) - RSU_APP_OFFSET
    print(f"  Payload:   {payload_size:,} bytes ({payload_size/1024:.1f} KB)")

    if diag:
        user_prog_size = end_addr - start_addr + 1
        const_data_size = df_end - df_start + 1 if df_flag else 0
        print(f"\n--- Diagnostics ---")
        print(f"  Expected user prog size:  {user_prog_size:,} bytes")
        print(f"  Expected data flash size: {const_data_size:,} bytes")
        print(f"  Expected total payload:   {user_prog_size + const_data_size:,} bytes")
        print(f"  Actual payload size:      {payload_size:,} bytes")
        print(f"  Signature hex: {signature.hex()}")

    # Verify signature
    if sig_type == SIG_TYPE_SHA256_ECDSA:
        user_prog_size = end_addr - start_addr + 1
        descriptor = data[0x200:0x300]
        code_flash = data[0x300:0x300 + user_prog_size]
        signed_data = descriptor + code_flash

        print(f"\nVerifying ECDSA signature ({sig_size} bytes over {len(signed_data):,} bytes)...")
        result = verify_ecdsa(signed_data, signature, key_path)
        if result:
            print("Result: PASS")
            return 0
        else:
            print("Result: FAIL")
            return 1
    elif sig_type == "hash-sha256":
        print(f"\nhash-sha256 verification not yet implemented")
        return 1
    else:
        print(f"\nVerification not implemented for: {sig_type}")
        return 1


# ==============================================================================
# Main
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert Motorola S-record (.mot) to Renesas Secure Update (.rsu) format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Convert .mot to .rsu:
    %(prog)s --mot aws_demos.mot --key sample_keys/secp256r1.privatekey -o userprog.rsu

  With custom sequence number:
    %(prog)s --mot aws_demos.mot --key sample_keys/secp256r1.privatekey -o userprog.rsu --seq-no 2

  Verify existing .rsu:
    %(prog)s --verify bin/updata/v202/userprog.rsu --key sample_keys/secp256r1.privatekey

  Verify with diagnostics:
    %(prog)s --verify bin/updata/v202/userprog.rsu --key sample_keys/secp256r1.privatekey --diag
        """,
    )

    parser.add_argument("--mot", type=Path,
                        help="Input .mot file path")
    parser.add_argument("--key", type=Path, required=True,
                        help="EC private key PEM file (secp256r1)")
    parser.add_argument("-o", "--output", type=Path,
                        help="Output .rsu file path")
    parser.add_argument("--seq-no", type=int, default=1,
                        help="Sequence number (default: 1, range: 1-4294967295)")
    parser.add_argument("--mcu", default="RX72N", choices=MCU_SPECS.keys(),
                        help="MCU type (default: RX72N)")
    parser.add_argument("--verify", type=Path, metavar="RSU_FILE",
                        help="Verify existing .rsu file instead of converting")
    parser.add_argument("--diag", action="store_true",
                        help="Print additional diagnostic information")

    args = parser.parse_args()

    mcu_spec = MCU_SPECS[args.mcu]

    # --- Verify mode ---
    if args.verify:
        if not args.verify.exists():
            print(f"ERROR: RSU file not found: {args.verify}")
            return 1
        if not args.key.exists():
            print(f"ERROR: Key file not found: {args.key}")
            return 1
        return verify_rsu(args.verify, args.key, mcu_spec, args.diag)

    # --- Convert mode ---
    if not args.mot:
        parser.error("--mot is required for conversion mode (use --verify for verification)")
    if not args.output:
        parser.error("--output (-o) is required for conversion mode")
    if not args.mot.exists():
        print(f"ERROR: MOT file not found: {args.mot}")
        return 1
    if not args.key.exists():
        print(f"ERROR: Key file not found: {args.key}")
        return 1
    if args.seq_no < 1 or args.seq_no > 0xFFFFFFFF:
        print(f"ERROR: Sequence number must be 1-4294967295, got {args.seq_no}")
        return 1

    print(f"=== mot_to_rsu converter ===")
    print(f"  MCU:     {args.mcu} (HW_ID=0x{mcu_spec['hardware_id']:08x})")
    print(f"  MOT:     {args.mot}")
    print(f"  Key:     {args.key}")
    print(f"  Output:  {args.output}")
    print(f"  Seq No:  {args.seq_no}")
    print()

    # Parse MOT file
    print("Parsing MOT file...")
    code_flash, data_flash = parse_mot_file(args.mot, mcu_spec)

    # Build RSU
    rsu_data = build_rsu(code_flash, data_flash, mcu_spec, args.key, args.seq_no)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'wb') as f:
        f.write(rsu_data)

    print(f"\nOutput: {args.output}")
    print(f"  Size: {len(rsu_data):,} bytes ({len(rsu_data)/1024:.1f} KB)")
    print(f"Done.")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
