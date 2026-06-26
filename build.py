#!/usr/bin/env python3
"""
NightWorld Build + Deploy + Launch Wrapper.
Builds the selected project(s) with Gradle, deploys JARs, and optionally launches Minecraft.

Usage:
    python build.py                           # builds Cosmetic + deploys
    python build.py MinecraftApi              # builds one project + deploys
    python build.py --all                     # builds all 5 projects + deploys
    python build.py --launch                  # build + deploy + launch game
    python build.py --java-home C:/jdk-17     # use portable JDK from folder
    python build.py --java-home C:/jdk/bin/java.exe  # java path auto-resolved
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

WORKSPACE = Path(__file__).parent.resolve()

PROJECTS = [
    "ReflectionTools",
    "LaunchLinker",
    "MinecraftApi",
    "MinecraftApi.Runtime",
    "Cosmetic",
]

DEPLOY_SCRIPT = WORKSPACE / "deploy.py"
CONFIG_FILE = WORKSPACE / "deploy.toml"


def find_gradlew(project_dir):
    if sys.platform == "win32":
        bat = project_dir / "gradlew.bat"
        if bat.exists():
            return str(bat)
    gradlew = project_dir / "gradlew"
    if gradlew.exists():
        return str(gradlew)
    return None


def resolve_java(java_home):
    """Resolve --java-home arg to JDK root and java executable."""
    if not java_home:
        return None, None
    p = Path(java_home).resolve()
    if p.name.lower() in ("java", "java.exe"):
        exe = p
        root = p.parent.parent
    elif p.name.lower() == "bin":
        exe = p / ("java.exe" if sys.platform == "win32" else "java")
        root = p.parent
    else:
        root = p
        exe = root / "bin" / ("java.exe" if sys.platform == "win32" else "java")
    return root, exe


def build_project(name, remap=False, java_home=None):
    project_dir = WORKSPACE / name
    if not project_dir.is_dir():
        print(f"  ✗ Project '{name}' not found at {project_dir}")
        return False

    gradlew = find_gradlew(project_dir)
    if not gradlew:
        print(f"  ✗ No gradlew script found in {project_dir}")
        return False

    cmd = [gradlew, "build"]

    if not remap and sys.platform != "win32":
        cmd.extend(["-x", "postBuild"])

    env = os.environ.copy()
    if java_home:
        jdk_root, _ = resolve_java(java_home)
        if jdk_root:
            env["JAVA_HOME"] = str(jdk_root)
            java_bin = jdk_root / "bin"
            env["PATH"] = str(java_bin) + os.pathsep + env.get("PATH", "")

    print(f"\n{'='*60}")
    print(f"  Building: {name}")
    print(f"  Command:  {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, cwd=project_dir, env=env)
    return result.returncode == 0


def run_deploy(dry_run=False, quiet=False):
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


def launch_game(java_home, dry_run=False):
    """Read [launch] from deploy.toml, substitute variables, and run."""
    if not CONFIG_FILE.exists():
        print("  ✗ deploy.toml not found — cannot launch")
        return 1

    with open(CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    config = data.get("launch", {})
    command_template = config.get("command", "")
    if not command_template:
        print("  ✗ No [launch] section or 'command' in deploy.toml")
        return 1

    # Resolve Java executable
    _, java_exe = resolve_java(java_home)
    if not java_exe or not java_exe.exists():
        print(f"  ✗ Java not found. Use --java-home or set JAVA_HOME")
        return 1

    # Read paths from config (explicit > derived from target)
    target = Path(data.get("target", "")).resolve()
    libs_cfg = config.get("libraries", "")
    root_cfg = config.get("root", "")
    # target = .../libraries/org/nightworld → parent.parent = .../libraries
    libraries = Path(libs_cfg).resolve() if libs_cfg else target.parent.parent
    root = Path(root_cfg).resolve() if root_cfg else target.parent.parent.parent

    # Substitute variables
    subs = {
        "{java}": str(java_exe),
        "{target}": str(target),
        "{libraries}": str(libraries),
        "{root}": str(root),
        "{cpsep}": ";" if sys.platform == "win32" else ":",
    }
    command = command_template
    for key, val in subs.items():
        command = command.replace(key, val)

    # Expand ${VAR} and %VAR% from environment
    command = os.path.expandvars(command)

    if dry_run:
        print(f"\n  [DRY-RUN] Would launch:\n")
        print(f"  {command[:200]}...")
        print(f"\n  (full command is {len(command)} characters)")
        return 0

    # Write command to a script file to bypass Windows cmd.exe 8191-char limit
    if sys.platform == "win32":
        ext = ".cmd"
    else:
        ext = ".sh"
    launch_file = WORKSPACE / f"launch_nwclient{ext}"
    launch_file.write_text(command, encoding="utf-8")
    if ext == ".sh":
        launch_file.chmod(0o755)

    print(f"\n  Launching Minecraft... (script: {launch_file})\n")
    subprocess.run(f'"{launch_file}"', shell=True)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Build NightWorld projects, deploy JARs, and optionally launch the game"
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
        help="Path to JDK installation or java.exe",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch Minecraft after build + deploy",
    )
    parser.add_argument(
        "--launch-only",
        action="store_true",
        help="Launch Minecraft without building (skips build + deploy)",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without executing",
    )
    args = parser.parse_args()

    # JAVA_HOME priority: CLI arg > deploy.toml > env var
    java_home = args.java_home
    if not java_home:
        try:
            with open(CONFIG_FILE, "rb") as f:
                cfg = tomllib.load(f)
            java_home = cfg.get("java_home", "")
        except Exception:
            java_home = ""
    if not java_home:
        java_home = os.environ.get("JAVA_HOME", "")

    # Determine which projects to build
    if args.all:
        to_build = PROJECTS
    elif args.projects:
        to_build = args.projects
    else:
        to_build = ["Cosmetic"]

    for name in to_build:
        if name not in PROJECTS:
            print(f"ERROR: Unknown project '{name}'. Available: {', '.join(PROJECTS)}")
            sys.exit(1)

    # Build
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
        if rc != 0:
            sys.exit(rc)

    # Launch (if --launch)
    if args.launch:
        rc = launch_game(java_home, dry_run=args.dry_run)
        sys.exit(rc)


if __name__ == "__main__":
    main()
