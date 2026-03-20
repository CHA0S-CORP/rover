#!/usr/bin/env python3
"""Firmware tool for Rove R2-4K-DUAL (SigmaStar SdUpgradeImage).

Binary layout of R2D.bin (parsed from the embedded U-Boot script):
  0x000000 .. 0x017FFF  Header script (partition/flash commands)
  0x018000              UBOOT (0x47208 bytes)
  0x060000              Kernel uImage (0x25EEF7 bytes)
  0x2BF000              Rootfs cpio.gz (0x899A2F bytes)
  0xB59000              UBIFS customer partition (0x1097000 bytes)

The header script contains hardcoded sizes for each fatload/nand write.
If the rootfs changes size, the header must be patched.
"""

import argparse
import gzip
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

# --- Layout constants (from header script analysis) ---
HEADER_END    = 0x018000
CPIO_OFFSET   = 0x2BF000
CPIO_SIZE_OEM = 0x899A2F   # original rootfs size in header script
UBIFS_OFFSET  = 0xB59000
UBIFS_SIZE    = 0x1097000

# Padding between rootfs end and UBIFS start
CPIO_REGION = UBIFS_OFFSET - CPIO_OFFSET  # 0x89A000 = 9,019,392


def find_bin(fw_dir: Path) -> Path:
    """Locate R2D.bin (original or backup)."""
    orig = fw_dir / "R2D.bin.orig"
    if orig.exists():
        return orig
    return fw_dir / "R2D.bin"


# ── extract ──────────────────────────────────────────────────────────────────

def cmd_extract(args):
    fw_dir = Path(args.fw_dir)
    bin_path = fw_dir / "R2D.bin"
    rootfs_dir = fw_dir / "rootfs"

    if not bin_path.exists():
        sys.exit(f"Error: {bin_path} not found")

    # Backup original if not already done
    orig = fw_dir / "R2D.bin.orig"
    if not orig.exists():
        print(f"Backing up original → {orig.name}")
        shutil.copy2(bin_path, orig)

    # Extract cpio.gz
    cpio_gz = fw_dir / "rootfs.cpio.gz"
    print(f"Extracting rootfs cpio.gz from 0x{CPIO_OFFSET:X} ({CPIO_SIZE_OEM} bytes)")
    with open(bin_path, "rb") as f:
        f.seek(CPIO_OFFSET)
        data = f.read(CPIO_SIZE_OEM)
    with open(cpio_gz, "wb") as f:
        f.write(data)
    print(f"  → {cpio_gz} ({len(data)} bytes)")

    # Extract rootfs
    if rootfs_dir.exists():
        if args.force:
            shutil.rmtree(rootfs_dir)
        else:
            print(f"  rootfs/ already exists (use --force to re-extract)")
            return

    rootfs_dir.mkdir()
    print(f"Extracting cpio archive → {rootfs_dir}/")
    subprocess.run(
        f'cd "{rootfs_dir}" && gunzip -c ../rootfs.cpio.gz | cpio -idm 2>/dev/null',
        shell=True, check=True,
    )
    file_count = sum(1 for _ in rootfs_dir.rglob("*") if _.is_file())
    print(f"  → {file_count} files extracted")


# ── build ────────────────────────────────────────────────────────────────────

def cmd_build(args):
    fw_dir = Path(args.fw_dir)
    rootfs_dir = fw_dir / "rootfs"
    bin_orig = find_bin(fw_dir)
    bin_out = fw_dir / "R2D.bin"

    if not rootfs_dir.exists():
        sys.exit(f"Error: {rootfs_dir} not found — run extract first")
    if not bin_orig.exists():
        sys.exit(f"Error: {bin_orig} not found")

    # 1. Repack cpio
    cpio_mod = fw_dir / "rootfs_mod.cpio.gz"
    print("Repacking rootfs cpio.gz ...")
    result = subprocess.run(
        f'cd "{rootfs_dir}" && find . | cpio -o -H newc 2>/dev/null | gzip -9',
        shell=True, capture_output=True, check=True,
    )
    cpio_data = result.stdout
    with open(cpio_mod, "wb") as f:
        f.write(cpio_data)

    new_size = len(cpio_data)
    print(f"  Original rootfs: {CPIO_SIZE_OEM:,} bytes (0x{CPIO_SIZE_OEM:X})")
    print(f"  Modified rootfs: {new_size:,} bytes (0x{new_size:X})")
    print(f"  Delta:           {new_size - CPIO_SIZE_OEM:+,} bytes")

    # 2. Read original binary
    with open(bin_orig, "rb") as f:
        orig_data = bytearray(f.read())

    # 3. Determine if UBIFS needs to shift
    # Align new UBIFS offset to 4KB boundary (NAND page alignment)
    ALIGN = 0x1000
    new_ubifs_offset = UBIFS_OFFSET
    if CPIO_OFFSET + new_size > UBIFS_OFFSET:
        raw = CPIO_OFFSET + new_size
        new_ubifs_offset = (raw + ALIGN - 1) & ~(ALIGN - 1)
        print(f"  Rootfs exceeds original region — shifting UBIFS:")
        print(f"    Old UBIFS offset: 0x{UBIFS_OFFSET:X}")
        print(f"    New UBIFS offset: 0x{new_ubifs_offset:X}")

    # 4. Patch header script for rootfs size and (optionally) UBIFS offset
    print("Patching header script ...")
    # The script is ASCII text terminated by "%" then padding.
    # Find the first non-ASCII or null byte to delimit the script.
    header_raw = bytes(orig_data[:HEADER_END])
    script_end = 0
    for i, b in enumerate(header_raw):
        if b == 0 or b > 127:
            script_end = i
            break
    script_text = header_raw[:script_end].decode("ascii")

    def hex_replace(text, old_val, new_val, label):
        """Replace all case variants of a hex value in the script."""
        old_variants = {
            f"0x{old_val:X}", f"0x{old_val:x}",
            f"0x{old_val:06X}", f"0x{old_val:06x}",
            f"0x{old_val:08X}", f"0x{old_val:08x}",
        }
        new_str = f"0x{new_val:X}"
        count = 0
        for v in old_variants:
            if v in text:
                n = text.count(v)
                text = text.replace(v, new_str)
                count += n
        if count == 0:
            pat = re.compile(f"0x0*{old_val:x}", re.IGNORECASE)
            text, count = pat.subn(new_str, text)
        if count:
            print(f"  {label}: 0x{old_val:X} → {new_str} ({count} occurrence{'s' if count != 1 else ''})")
        else:
            print(f"  WARNING: {label}: could not find 0x{old_val:X}")
        return text

    patched = script_text
    if new_size != CPIO_SIZE_OEM:
        patched = hex_replace(patched, CPIO_SIZE_OEM, new_size, "rootfs size")
    if new_ubifs_offset != UBIFS_OFFSET:
        patched = hex_replace(patched, UBIFS_OFFSET, new_ubifs_offset, "customer offset")

    patched_bytes = patched.encode("ascii")
    if len(patched_bytes) > script_end:
        sys.exit(
            f"Error: patched header script is {len(patched_bytes) - script_end} bytes "
            f"longer than original — hex values grew in length. Cannot fit."
        )
    patched_bytes = patched_bytes + b"\x00" * (script_end - len(patched_bytes))
    orig_data[:script_end] = patched_bytes

    # 5. Build output binary
    print("Assembling R2D.bin ...")

    # Extract UBIFS + trailing data BEFORE overwriting (rootfs may overlap)
    ubifs_data = bytes(orig_data[UBIFS_OFFSET:UBIFS_OFFSET + UBIFS_SIZE])
    trailing_data = b""
    with open(bin_orig, "rb") as f:
        f.seek(UBIFS_OFFSET + UBIFS_SIZE)
        trailing_data = f.read()

    # Write modified rootfs (may extend past original UBIFS offset)
    orig_data[CPIO_OFFSET:CPIO_OFFSET + new_size] = cpio_data

    if new_ubifs_offset != UBIFS_OFFSET:
        # Pad between rootfs end and new UBIFS offset
        pad_start = CPIO_OFFSET + new_size
        pad_len = new_ubifs_offset - pad_start
        if pad_len > 0:
            orig_data[pad_start:new_ubifs_offset] = b"\xff" * pad_len
        # Place UBIFS at new offset (may need to extend the bytearray)
        new_end = new_ubifs_offset + UBIFS_SIZE
        if new_end > len(orig_data):
            orig_data.extend(b"\xff" * (new_end - len(orig_data)))
        orig_data[new_ubifs_offset:new_ubifs_offset + UBIFS_SIZE] = ubifs_data
        # Append trailing data (misc partition, etc.) shifted by same delta
        if trailing_data:
            shift = new_ubifs_offset - UBIFS_OFFSET
            trailing_start = UBIFS_OFFSET + UBIFS_SIZE + shift
            trailing_end = trailing_start + len(trailing_data)
            if trailing_end > len(orig_data):
                orig_data.extend(b"\xff" * (trailing_end - len(orig_data)))
            orig_data[trailing_start:trailing_end] = trailing_data
            orig_data = orig_data[:trailing_end]
    else:
        # Pad remainder of rootfs region with 0xFF
        if new_size < CPIO_REGION:
            pad_start = CPIO_OFFSET + new_size
            orig_data[pad_start:UBIFS_OFFSET] = b"\xff" * (UBIFS_OFFSET - pad_start)

    # 6. Write output
    with open(bin_out, "wb") as f:
        f.write(orig_data)
    print(f"  → {bin_out} ({len(orig_data):,} bytes)")

    # 7. Verify
    print("Verifying ...")
    with open(bin_out, "rb") as f:
        f.seek(CPIO_OFFSET)
        magic = f.read(2)
        assert magic == bytes([0x1f, 0x8b]), f"Bad gzip magic at rootfs offset: {magic.hex()}"
        f.seek(new_ubifs_offset)
        ubifs_magic = struct.unpack("<I", f.read(4))[0]
        assert ubifs_magic == 0x06101831, f"Bad UBIFS magic at 0x{new_ubifs_offset:X}: 0x{ubifs_magic:08X}"
    print(f"  gzip magic at 0x{CPIO_OFFSET:X}: OK")
    print(f"  UBIFS magic at 0x{new_ubifs_offset:X}: OK")
    print("Build complete.")


# ── tar ──────────────────────────────────────────────────────────────────────

def cmd_tar(args):
    fw_dir = Path(args.fw_dir)
    bin_path = fw_dir / "R2D.bin"
    tar_out = fw_dir / "R2D.tar"

    if not bin_path.exists():
        sys.exit(f"Error: {bin_path} not found — run build first")

    components = ["IPL", "IPL_CUST", "UBOOT", "R2D.bin"]
    for c in components:
        if not (fw_dir / c).exists():
            sys.exit(f"Error: {fw_dir / c} not found")

    print(f"Creating {tar_out} ...")
    subprocess.run(
        ["tar", "cf", str(tar_out)] + components,
        cwd=str(fw_dir), check=True,
    )
    size = tar_out.stat().st_size
    print(f"  → {tar_out} ({size:,} bytes)")


# ── flash-sd ─────────────────────────────────────────────────────────────────

def cmd_flash_sd(args):
    fw_dir = Path(args.fw_dir)
    bin_path = fw_dir / "R2D.bin"

    if not bin_path.exists():
        sys.exit(f"Error: {bin_path} not found — run build first")

    sd_path = Path(args.sd_path)
    if not sd_path.is_dir():
        sys.exit(f"Error: SD card mount not found at {sd_path}")

    # U-Boot's fatload reads from $(SdUpgradeImage) at offsets matching
    # R2D.bin's layout. The file on SD must be the raw R2D.bin, not a tar.
    dest = sd_path / "SigmastarUpgradeSD.bin"
    print(f"Copying {bin_path.name} → {dest}")
    shutil.copy2(bin_path, dest)
    size = dest.stat().st_size
    print(f"  → {dest} ({size:,} bytes)")
    print()
    print("Eject the SD card, insert into camera, and power on.")
    print("DO NOT power off during flashing (LED will blink).")


# ── info ─────────────────────────────────────────────────────────────────────

def cmd_info(args):
    fw_dir = Path(args.fw_dir)
    bin_path = fw_dir / "R2D.bin"
    if not bin_path.exists():
        sys.exit(f"Error: {bin_path} not found")

    size = bin_path.stat().st_size
    print(f"Firmware: {bin_path}")
    print(f"Size:     {size:,} bytes (0x{size:X})")
    print()

    with open(bin_path, "rb") as f:
        # Header script
        header = f.read(HEADER_END)
        script_end = header.find(b"\x00\x00")
        script = header[:script_end].decode("ascii", errors="replace")

        # Extract partition info from fatload lines
        print("Partitions (from header script):")
        current_part = None
        for line in script.splitlines():
            m = re.match(r"# File Partition: (.+)", line)
            if m:
                current_part = m.group(1)
            m2 = re.match(
                r"fatload mmc 0 0x\w+ \$\(SdUpgradeImage\) (0x\w+) (0x\w+)", line
            )
            if m2 and current_part:
                fsize = int(m2.group(1), 16)
                foffset = int(m2.group(2), 16)
                print(f"  {current_part:25s}  offset=0x{foffset:08X}  size={fsize:>10,} (0x{fsize:X})")

        # Find actual customer offset from header (may differ from constant if rebuilt)
        customer_offset = UBIFS_OFFSET
        in_customer = False
        for line in script.splitlines():
            if "customer" in line.lower():
                in_customer = True
            if in_customer:
                m3 = re.match(
                    r"fatload mmc 0 0x\w+ \$\(SdUpgradeImage\) (0x\w+) (0x\w+)", line
                )
                if m3:
                    customer_offset = int(m3.group(2), 16)
                    break

        # Verify magics
        print()
        f.seek(CPIO_OFFSET)
        gzip_magic = f.read(2)
        gzip_ok = gzip_magic == bytes([0x1f, 0x8b])
        print(f"Rootfs gzip magic:  {gzip_magic.hex()} {'OK' if gzip_ok else 'BAD'}")

        f.seek(customer_offset)
        ubifs_val = struct.unpack("<I", f.read(4))[0]
        ubifs_ok = ubifs_val == 0x06101831
        print(f"UBIFS magic:        0x{ubifs_val:08X} at 0x{customer_offset:X} {'OK' if ubifs_ok else 'BAD'}")

    # Check for backup
    orig = fw_dir / "R2D.bin.orig"
    if orig.exists():
        print(f"\nOriginal backup:    {orig} ({orig.stat().st_size:,} bytes)")

    # Check default.ini diff
    ini_path = fw_dir / "rootfs" / "bootconfig" / "bin" / "default.ini"
    ini_bak = ini_path.with_suffix(".ini.bak")
    if ini_path.exists() and ini_bak.exists():
        result = subprocess.run(
            ["diff", "-u", str(ini_bak), str(ini_path)],
            capture_output=True, text=True,
        )
        if result.stdout:
            print(f"\ndefault.ini changes:")
            print(result.stdout)
        else:
            print(f"\ndefault.ini: no changes from backup")
    elif ini_path.exists():
        print(f"\ndefault.ini: present (no .bak for comparison)")


# ── diff ─────────────────────────────────────────────────────────────────────

def cmd_diff(args):
    fw_dir = Path(args.fw_dir)
    ini_path = fw_dir / "rootfs" / "bootconfig" / "bin" / "default.ini"
    ini_bak = ini_path.with_suffix(".ini.bak")

    if not ini_path.exists():
        sys.exit(f"Error: {ini_path} not found")

    if ini_bak.exists():
        ref = ini_bak
    else:
        # Try extracting from original binary
        orig = fw_dir / "R2D.bin.orig"
        if not orig.exists():
            orig = fw_dir / "R2D.bin"
        if not orig.exists():
            sys.exit("No reference file found (.bak or R2D.bin.orig)")

        # Extract to temp and diff
        print("(extracting original rootfs for comparison)")
        ref_dir = Path(tempfile.mkdtemp())
        try:
            with open(orig, "rb") as f:
                f.seek(CPIO_OFFSET)
                cpio_data = f.read(CPIO_SIZE_OEM)
            cpio_gz_path = ref_dir / "rootfs.cpio.gz"
            with open(cpio_gz_path, "wb") as gz:
                gz.write(cpio_data)
            subprocess.run(
                f'cd "{ref_dir}" && gunzip -c rootfs.cpio.gz | cpio -idm 2>/dev/null',
                shell=True,
            )
            ref = ref_dir / "bootconfig" / "bin" / "default.ini"
            if not ref.exists():
                sys.exit("Could not extract original default.ini")
            result = subprocess.run(
                ["diff", "-u", str(ref), str(ini_path)],
                capture_output=True, text=True,
            )
            print(result.stdout or "(no differences)")
            return
        finally:
            shutil.rmtree(ref_dir, ignore_errors=True)

    result = subprocess.run(
        ["diff", "-u", str(ref), str(ini_path)],
        capture_output=True, text=True,
    )
    print(result.stdout or "(no differences)")


# ── restore ──────────────────────────────────────────────────────────────────

def cmd_restore(args):
    fw_dir = Path(args.fw_dir)
    orig = fw_dir / "R2D.bin.orig"
    target = fw_dir / "R2D.bin"

    if not orig.exists():
        sys.exit(f"Error: {orig} not found — no backup to restore from")

    print(f"Restoring {orig.name} → {target.name}")
    shutil.copy2(orig, target)
    print("Done. Run 'make tar' and 'make flash-sd' to flash stock firmware.")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Rove R2-4K firmware build tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--fw-dir", default=".",
        help="Firmware directory containing R2D.bin and rootfs/ (default: .)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("extract", help="Extract rootfs from R2D.bin")
    sp.add_argument("--force", action="store_true", help="Re-extract even if rootfs/ exists")

    sub.add_parser("build", help="Repack rootfs and rebuild R2D.bin")
    sub.add_parser("tar", help="Create R2D.tar for flashing")

    sp = sub.add_parser("flash-sd", help="Copy firmware to SD card")
    sp.add_argument("sd_path", help="SD card mount point (e.g. /Volumes/SDCARD)")

    sub.add_parser("info", help="Show firmware layout and verify integrity")
    sub.add_parser("diff", help="Show default.ini changes from stock")
    sub.add_parser("restore", help="Restore original R2D.bin from backup")

    args = p.parse_args()
    dispatch = {
        "extract": cmd_extract,
        "build": cmd_build,
        "tar": cmd_tar,
        "flash-sd": cmd_flash_sd,
        "info": cmd_info,
        "diff": cmd_diff,
        "restore": cmd_restore,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
