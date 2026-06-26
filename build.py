#!/usr/bin/env python3
"""
NightWorld Build + Deploy Wrapper.
Builds the selected project(s) with Gradle, then deploys JARs.

Usage:
    python build.py                           # builds Cosmetic + deploys
    python build.py MinecraftApi              # builds one project + deploys
    python build.py MinecraftApi Cosmetic     # builds multiple + deploys
    python build.py --all                     # builds all 5 projects + deploys
    python build.py --no-deploy               # build only, skip deploy
    python build.py --remap                   # include remapping (Windows only,
                                              # runs postBuild which calls remapping.bat)
    python build.py --java-home C:/jdk-17     # use portable JDK from folder
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

WORKSPACE = Path(__file__).parent.resolve()

# All projects in dependency order (safe for --all)
PROJECTS = [
    "ReflectionTools",
    "LaunchLinker",
    "MinecraftApi",
    "MinecraftApi.Runtime",
    "Cosmetic",
]

DEPLOY_SCRIPT = WORKSPACE / "deploy.py"


def find_gradlew(project_dir):
    """Return the gradlew script path (supports Windows and Unix)."""
    if sys.platform == "win32":
        bat = project_dir / "gradlew.bat"
        if bat.exists():
            return str(bat)
    gradlew = project_dir / "gradlew"
    if gradlew.exists():
        return str(gradlew)
    return None


def build_project(name, remap=False, java_home=None):
    """Run ./gradlew build in a project directory. Returns True on success."""
    project_dir = WORKSPACE / name
    if not project_dir.is_dir():
        print(f"  ✗ Project '{name}' not found at {project_dir}")
        return False

    gradlew = find_gradlew(project_dir)
    if not gradlew:
        print(f"  ✗ No gradlew script found in {project_dir}")
        return False

    cmd = [gradlew, "build"]

    # remapping.bat runs via cmd.exe — only available on Windows
    if not remap and sys.platform != "win32":
        cmd.extend(["-x", "postBuild"])

    # Prepare environment with custom JAVA_HOME if provided
    env = os.environ.copy()
    if java_home:
        java_home = Path(java_home).resolve()
        if java_home.name.lower() in ("java", "java.exe"):
            java_home = java_home.parent.parent
        elif java_home.name.lower() == "bin":
            java_home = java_home.parent
        env["JAVA_HOME"] = str(java_home)
        java_bin = java_home / "bin"
        env["PATH"] = str(java_bin) + os.pathsep + env.get("PATH", "")

    print(f"\n{'='*60}")
    print(f"  Building: {name}")
    print(f"  Command:  {' '.join(cmd)}")
    if java_home:
        print(f"  Java home: {java_home}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=project_dir, env=env)
    return result.returncode == 0


def run_deploy(dry_run=False, quiet=False):
    """Run deploy.py and return its exit code."""
    if not DEPLOY_SCRIPT.exists():
        print(f"  ✗ deploy.py not found at {DEPLOY_SCRIPT}")
        return 1

    cmd = [sys.executable, str(DEPLOY_SCRIPT)]
    if dry_run:
        cmd.append("--dry-run")
    if quiet:
        cmd.append("--quiet")

    print(f"\n  Deploying...\n")
    result = subprocess.run(cmd, cwd=WORKSPACE)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Build NightWorld projects and deploy JARs"
    )
    parser.add_argument(
        "projects",
        nargs="*",
        help="Project(s) to build (default: Cosmetic). Use --all for all 5.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build all 5 projects in dependency order",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Build only, skip deployment",
    )
    parser.add_argument(
        "--remap",
        action="store_true",
        help="Run postBuild remapping (Windows only, requires remapping.bat)",
    )
    parser.add_argument(
        "--java-home",
        type=str,
        default=None,
        help="Path to JDK installation (set JAVA_HOME for Gradle)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Build then show deploy preview without copying",
    )
    args = parser.parse_args()

    # JAVA_HOME: CLI arg > env var
    java_home = args.java_home or os.environ.get("JAVA_HOME")

    # Determine which projects to build
    if args.all:
        to_build = PROJECTS
    elif args.projects:
        to_build = args.projects
    else:
        to_build = ["Cosmetic"]

    # Validate project names
    for name in to_build:
        if name not in PROJECTS:
            print(f"ERROR: Unknown project '{name}'. Available: {', '.join(PROJECTS)}")
            sys.exit(1)

    # Build each project
    all_ok = True
    for name in to_build:
        ok = build_project(name, remap=args.remap, java_home=java_home)
        if not ok:
            print(f"\n  ✗ Build FAILED: {name}")
            all_ok = False
        else:
            print(f"\n  ✓ Build succeeded: {name}")

    if not all_ok:
        print("\nOne or more builds failed. Deploy skipped.")
        sys.exit(1)

    # Deploy (unless --no-deploy)
    if args.no_deploy:
        print("\nBuild complete. Skipping deploy (--no-deploy).")
    else:
        rc = run_deploy(dry_run=args.dry_run)
        sys.exit(rc)


if __name__ == "__main__":
    main()
