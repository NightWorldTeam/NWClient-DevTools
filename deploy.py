#!/usr/bin/env python3
"""
NightWorld Build Deployer — Copies built JARs to a target Minecraft directory.
Reads deploy.toml for configuration.

Usage:
    python deploy.py                           # normal deploy
    python deploy.py --dry-run                 # preview without copying
    python deploy.py --quiet                   # minimal output
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

WORKSPACE = Path(__file__).parent.resolve()
CONFIG_FILE = WORKSPACE / "deploy.toml"


def parse_config():
    """Parse deploy.toml and return (target_dir, list_of_mappings)."""
    if not CONFIG_FILE.exists():
        print(f"ERROR: config not found at {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    target_dir = data.get("target")
    if not target_dir:
        print("ERROR: 'target' not set in deploy.toml")
        sys.exit(1)

    target_dir = os.path.expandvars(target_dir)
    target = Path(target_dir)
    if not target.is_absolute():
        target = (WORKSPACE / target).resolve()

    projects = data.get("projects", {})
    mappings = []

    def collect_mappings(project_name, rules):
        for key, value in rules.items():
            if isinstance(value, str):
                mappings.append({
                    "project": project_name,
                    "pattern": key,
                    "dest": value,
                })
            elif isinstance(value, dict):
                collect_mappings(f"{project_name}.{key}", value)

    for project_name, rules in projects.items():
        collect_mappings(project_name, rules)

    return target, mappings


def deploy(dry_run=False, quiet=False):
    target, mappings = parse_config()

    if not quiet:
        print(f"Deploy target : {target}")
        print(f"Mappings      : {len(mappings)} rule(s)")
        print()

    copied = 0

    for mapping in mappings:
        project_dir = WORKSPACE / mapping["project"]
        if not project_dir.is_dir():
            if not quiet:
                print(f"  ~ {mapping['project']}: directory not found, skipping")
            continue

        matches = sorted(project_dir.glob(mapping["pattern"]))
        if not matches:
            if not quiet:
                print(f"  - {mapping['project']}: no files matching '{mapping['pattern']}'")
            continue

        dest_dir = target / mapping["dest"]
        if not dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        for src in matches:
            if not src.is_file():
                continue
            dest = dest_dir / src.name
            copied += 1

            if dry_run:
                print(f"  [DRY-RUN] {src.relative_to(WORKSPACE)}  →  {dest}")
            else:
                shutil.copy2(src, dest)
                if not quiet:
                    print(f"  ✓ {src.relative_to(WORKSPACE)}  →  {dest}")

    if dry_run:
        print(f"\nDry-run complete. Would copy {copied} file(s).")
    else:
        print(f"\nDeploy complete. Copied {copied} file(s) to {target}")

    return copied


def main():
    parser = argparse.ArgumentParser(
        description="Deploy NightWorld built JARs to target directory"
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be copied without copying",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress verbose per-file output",
    )
    args = parser.parse_args()

    deploy(dry_run=args.dry_run, quiet=args.quiet)


if __name__ == "__main__":
    main()
