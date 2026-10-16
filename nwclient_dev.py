#!/usr/bin/env python3
"""Launch NWClient using a local, uncommitted profile and staged Vanilla JARs.

Never prints the launch command or writes secrets to a batch/shell script.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent
STAGED = ROOT / "build" / "dev-artifacts"
CONFIG = ROOT / "deploy.toml"
DIRECTORIES = ("Cosmetics/1.0", "MinecraftApi/1.0", "MinecraftApi.Runtime/1.0",
               "LaunchLinker/1.0", "ReflectionTools/1.0")
JDWP = "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=127.0.0.1:5005"


def absolute(value):
    result = Path(os.path.expanduser(os.path.expandvars(str(value))))
    return (result if result.is_absolute() else ROOT / result).resolve()


def java_path(config):
    chosen = config.get("java_home") or os.environ.get("NW_DEV_JAVA") or os.environ.get("JAVA_HOME")
    if chosen:
        path = absolute(chosen)
        if path.is_dir():
            if path.name.lower() != "bin":
                path /= "bin"
            path /= "java.exe"
    else:
        found = shutil.which("java.exe")
        if not found:
            raise ValueError("JDK 17 not found; configure java_home in deploy.toml.")
        path = Path(found)
    if not path.is_file():
        raise ValueError("Configured Java executable is missing.")
    return path


def run(debug=False):
    if os.name != "nt":
        raise ValueError("This experimental Vanilla dev profile requires Windows.")
    if not CONFIG.is_file():
        raise ValueError("Create local deploy.toml from example.deploy.toml; do not commit secrets.")
    with CONFIG.open("rb") as stream:
        config = tomllib.load(stream)
    launch = config.get("launch", {})
    if not config.get("target") or not launch.get("command"):
        raise ValueError("deploy.toml requires target and [launch].command.")

    staged = []
    for folder in DIRECTORIES:
        files = list((STAGED / folder).glob("*.jar"))
        if len(files) != 1:
            raise ValueError(f"Expected exactly one JAR in build/dev-artifacts/{folder}.")
        staged.append((files[0], Path(folder) / files[0].name))

    command = launch["command"]
    missing = [source.name for source, _ in staged if source.name not in command]
    if missing:
        raise ValueError("Launch classpath does not reference the staged dev JARs: "
                         + ", ".join(missing))

    target = absolute(config["target"])
    libraries = absolute(launch["libraries"]) if launch.get("libraries") else target.parent.parent
    game_root = absolute(launch["root"]) if launch.get("root") else libraries.parent

    # Insert JDWP immediately after the Java executable, respecting quotes.
    if '"{java}"' not in command:
        command = command.replace('{java}', '"{java}"', 1)
    if debug:
        command = command.replace('"{java}"', '"{java}" ' + JDWP, 1)
    for name, value in {
        "{java}": str(java_path(config)),
        "{target}": str(target),
        "{libraries}": str(libraries),
        "{root}": str(game_root),
        "{cpsep}": ";",
    }.items():
        command = command.replace(name, value)
    command = os.path.expandvars(command)
    if re.search(r"\$\{[A-Za-z_]\w*\}|%[A-Za-z_]\w*%", command):
        raise ValueError("Launch profile contains an unresolved environment variable.")
    if "{java}" in command or "{target}" in command or "{libraries}" in command:
        raise ValueError("Launch profile contains an unresolved placeholder.")

    print(f"Deploying {len(staged)} NWClient dev artifacts to {target}")
    for source, relative in staged:
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".nwclient-tmp")
        try:
            shutil.copy2(source, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        print(f"  {relative}")

    print("Starting Minecraft. Launch arguments and credentials are hidden.")
    if debug:
        print("Attach Java debugger to 127.0.0.1:5005")
    try:
        # Direct Windows CreateProcessW avoids the 8191-char cmd.exe limit and
        # never stores tokens in a generated .cmd or .sh file.
        result = subprocess.run(command, shell=False, cwd=ROOT, check=False)
    except OSError as error:
        raise ValueError(f"Java process could not start: {error.strerror}") from None
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"run", "debug"}:
        print("Usage: nwclient_dev.py run|debug", file=sys.stderr)
        sys.exit(2)
    try:
        sys.exit(run(debug=sys.argv[1] == "debug"))
    except (ValueError, OSError) as error:
        print(f"NWClient dev: {error}", file=sys.stderr)
        sys.exit(1)
