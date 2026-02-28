#!/usr/bin/env python3
"""
resolve_fit_modules.py - RX e2studio FIT Module Resolver

Parses .scfg files to identify required FIT modules, checks local availability,
and downloads missing modules from the RX Driver Package on GitHub.

Usage:
    python resolve_fit_modules.py <scfg_file_or_dir> [--fit-dir <path>] [--dry-run]

Arguments:
    scfg_file_or_dir  Path to a .scfg file or directory containing .scfg files

Options:
    --fit-dir <path>  Path to local FITModules folder
                      (default: ~/.eclipse/com.renesas.platform_download/FITModules)
    --dry-run         Show what would be downloaded without actually downloading
    --verbose         Show detailed progress

Background:
    Smart Configurator (SMC) in e2studio generates FIT module code based on
    the module versions recorded in .scfg files. If the required version is
    not present in the local FITModules folder, SMC silently skips code
    generation, causing build errors (missing source files).

    This script automates the resolution by:
    1. Parsing .scfg XML to extract required FIT module names and versions
    2. Checking the local FITModules folder for availability
    3. Fetching versions.xml from https://github.com/renesas/rx-driver-package
       to resolve download URLs for missing modules
    4. Downloading .zip, .xml, and .mdf files to the local FITModules folder

    After running this script, re-open the project in e2studio and run
    Smart Configurator code generation to populate smc_gen/ directories.
"""

import argparse
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

VERSIONS_XML_URL = "https://raw.githubusercontent.com/renesas/rx-driver-package/master/versions.xml"


def find_scfg_files(path: str) -> list[str]:
    """Find .scfg files in the given path."""
    p = Path(path)
    if p.is_file() and p.suffix == ".scfg":
        return [str(p)]
    elif p.is_dir():
        return sorted(str(f) for f in p.rglob("*.scfg"))
    else:
        print(f"Error: {path} is not a .scfg file or directory", file=sys.stderr)
        sys.exit(1)


def parse_scfg(scfg_path: str) -> list[dict]:
    """Parse a .scfg file and return list of required FIT modules."""
    tree = ET.parse(scfg_path)
    root = tree.getroot()
    modules = []
    for comp in root.iter("component"):
        display = comp.get("display", "")
        version = comp.get("version", "")
        comp_id = comp.get("id", "")
        if display and version:
            modules.append({
                "name": display,
                "version": version,
                "id": comp_id,
                "scfg": os.path.basename(scfg_path),
            })
    return modules


def get_default_fit_dir() -> str:
    """Get the default FITModules directory path."""
    home = Path.home()
    return str(home / ".eclipse" / "com.renesas.platform_download" / "FITModules")


def check_local(fit_dir: str, name: str, version: str) -> bool:
    """Check if a FIT module is available locally."""
    expected = f"{name}_v{version}.zip"
    return os.path.exists(os.path.join(fit_dir, expected))


def fetch_versions_xml(verbose: bool = False) -> ET.Element:
    """Download and parse versions.xml from rx-driver-package."""
    if verbose:
        print(f"  Fetching {VERSIONS_XML_URL}...")
    req = urllib.request.Request(VERSIONS_XML_URL)
    with urllib.request.urlopen(req) as resp:
        content = resp.read()
    return ET.fromstring(content)


def build_url_map(vroot: ET.Element) -> dict:
    """Build a map of module_name|version -> {zip_basename, urls}."""
    url_map = {}
    for mod in vroot.findall("module"):
        name_el = mod.find("name")
        ver_el = mod.find("version")
        urls_el = mod.find("urls")
        if name_el is None or ver_el is None or urls_el is None:
            continue
        mod_name = (name_el.text or "").strip()
        mod_ver = (ver_el.text or "").strip()

        urls = {}
        for url_el in urls_el.findall("url"):
            url = (url_el.text or "").strip()
            if url.endswith(".zip"):
                urls["zip"] = url
            elif url.endswith(".xml"):
                urls["xml"] = url
            elif url.endswith(".mdf"):
                urls["mdf"] = url

        if mod_name and mod_ver and "zip" in urls:
            zip_basename = urls["zip"].rsplit("/", 1)[-1][:-4]  # remove .zip
            key = f"{mod_name}|{mod_ver}"
            url_map[key] = {"zip_basename": zip_basename, "urls": urls}
    return url_map


def download_file(url: str, dest: str, verbose: bool = False) -> bool:
    """Download a file from URL to dest path."""
    try:
        if verbose:
            print(f"    Downloading {os.path.basename(dest)}...")
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        if size < 100:
            # Likely an error page
            print(f"    WARNING: {os.path.basename(dest)} is only {size} bytes", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"    ERROR: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Resolve missing FIT modules for RX e2studio projects"
    )
    parser.add_argument(
        "path",
        help="Path to .scfg file or directory containing .scfg files",
    )
    parser.add_argument(
        "--fit-dir",
        default=get_default_fit_dir(),
        help="Path to local FITModules folder (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without downloading",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed progress",
    )
    args = parser.parse_args()

    # Step 1: Find and parse .scfg files
    scfg_files = find_scfg_files(args.path)
    if not scfg_files:
        print("No .scfg files found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(scfg_files)} .scfg file(s)")

    all_modules = {}
    for scfg in scfg_files:
        modules = parse_scfg(scfg)
        for m in modules:
            key = f"{m['name']}|{m['version']}"
            if key not in all_modules:
                all_modules[key] = m
                all_modules[key]["scfg_files"] = []
            all_modules[key]["scfg_files"].append(m["scfg"])

    print(f"Required FIT modules: {len(all_modules)}")

    # Step 2: Check local availability
    if not os.path.isdir(args.fit_dir):
        print(f"Error: FITModules directory not found: {args.fit_dir}", file=sys.stderr)
        sys.exit(1)

    local_zips = {f[:-4] for f in os.listdir(args.fit_dir) if f.endswith(".zip")}

    missing = []
    found = 0
    for key, m in sorted(all_modules.items()):
        local_name = f"{m['name']}_v{m['version']}"
        if local_name in local_zips:
            found += 1
            if args.verbose:
                print(f"  OK  {m['name']} v{m['version']}")
        else:
            missing.append(m)

    print(f"Found locally: {found}")
    print(f"Missing: {len(missing)}")

    if not missing:
        print("\nAll FIT modules are available. No downloads needed.")
        return

    # Step 3: Fetch versions.xml and resolve URLs
    print(f"\nFetching versions.xml from rx-driver-package...")
    vroot = fetch_versions_xml(args.verbose)
    url_map = build_url_map(vroot)
    print(f"versions.xml contains {len(url_map)} module entries")

    # Step 4: Download missing modules
    downloadable = []
    not_found = []
    for m in missing:
        vkey = f"{m['name']}|{m['version']}"
        if vkey in url_map:
            entry = url_map[vkey]
            # Check if already downloaded with different naming
            if entry["zip_basename"] in local_zips:
                found += 1
                if args.verbose:
                    print(f"  OK  {m['name']} v{m['version']} (as {entry['zip_basename']})")
                continue
            downloadable.append((m, entry))
        else:
            not_found.append(m)

    if not_found:
        print(f"\nWARNING: {len(not_found)} module(s) not found in versions.xml:")
        for m in not_found:
            print(f"  {m['name']} v{m['version']} (used by: {', '.join(m['scfg_files'])})")

    if not downloadable:
        if not not_found:
            print("\nAll FIT modules are available. No downloads needed.")
        return

    print(f"\nModules to download: {len(downloadable)}")
    for m, entry in downloadable:
        print(f"  {m['name']} v{m['version']} -> {entry['zip_basename']}")

    if args.dry_run:
        print("\n[DRY RUN] No files were downloaded.")
        return

    print(f"\nDownloading to {args.fit_dir}...")
    success = 0
    fail = 0
    for m, entry in downloadable:
        print(f"  {m['name']} v{m['version']}:")
        all_ok = True
        for ext, url in entry["urls"].items():
            filename = url.rsplit("/", 1)[-1]
            dest = os.path.join(args.fit_dir, filename)
            if not download_file(url, dest, args.verbose):
                all_ok = False
        if all_ok:
            success += 1
        else:
            fail += 1

    print(f"\nDone: {success} downloaded, {fail} failed")
    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
