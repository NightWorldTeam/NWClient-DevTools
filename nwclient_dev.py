#!/usr/bin/env python3
"""Run the default offline NWClient dev profile without any user config file.

The client loads the FIVE staged workspace JARs directly. Existing installed
NWClient library JARs are never overwritten, and no login secrets are used.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
STAGED = WORKSPACE / "build" / "dev-artifacts"
TEMPLATE = WORKSPACE / "dev-launch-template.txt"
DEV_JARS = (
    "Cosmetics/1.0",
    "MinecraftApi/1.0",
    "MinecraftApi.Runtime/1.0",
    "LaunchLinker/1.0",
    "ReflectionTools/1.0",
)
JDWP = "-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=127.0.0.1:5005"


def java_executable(game_root):
    candidates = [
        game_root / "java" / "versions" / "java-runtime-gamma" / "bin" / "java.exe",
    ]
    for name in ("NW_DEV_JAVA", "JAVA_HOME"):
        value = os.environ.get(name)
        if not value:
            continue
        path = Path(value).expanduser()
        if path.is_dir():
            if path.name.lower() != "bin":
                path /= "bin"
            path /= "java.exe"
        candidates.append(path)
    found = shutil.which("java.exe")
    if found:
        candidates.append(Path(found))
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise ValueError(
        "Java was not found. Launch NWLauncher once to install Java, "
        "or set JAVA_HOME to a Java 17 JDK."
    )


def validate_files():
    if os.name != "nt":
        raise ValueError("The existing NWClient Vanilla dev profile requires Windows.")
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise ValueError("APPDATA is missing; this dev profile requires a Windows user session.")
    game_root = Path(appdata).resolve() / ".lexplosion"
    libraries = game_root / "libraries"
    client_jar = game_root / "instances" / "nwclient dev" / "version" / "client.jar"
    for description, path in (
        ("launcher libraries", libraries),
        ("launcher assets", game_root / "assets"),
        ("launcher Minecraft client", client_jar),
        ("default launch template", TEMPLATE),
    ):
        if not path.exists():
            raise ValueError(
                f"Missing {description}: {path}. Install/start the NWLauncher "
                "Minecraft 1.20 dev profile once before running the workspace."
            )
    staged = []
    for directory in DEV_JARS:
        files = sorted((STAGED / directory).glob("*.jar"))
        if len(files) != 1:
            raise ValueError(
                f"Expected one staged JAR in build/dev-artifacts/{directory}, "
                f"found {len(files)}. Run devPrepare first."
            )
        staged.append(files[0])
    return game_root, libraries, staged


def make_command(game_root, libraries, staged, debug):
    template = "\n".join(
        line.strip() for line in TEMPLATE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    if (
        "authlib-injector" in template
        or "prefetched" in template
        or "--clientId" in template
        or "--xuid" in template
        or "--accessToken 0" not in template
    ):
        raise ValueError("Unsafe local launch template: offline auth settings are invalid.")
    absent = [file.name for file in staged if file.name not in template]
    if absent:
        raise ValueError(
            "The default classpath needs an update to match built JARs: "
            + ", ".join(absent)
        )

    # The staged layout exactly mirrors the launcher's namespace directory.
    # This avoids copying over any files of the user's launcher installation.
    command = template
    if '"{java}"' not in command:
        command = command.replace("{java}", '"{java}"', 1)
    if debug:
        command = command.replace('"{java}"', '"{java}" ' + JDWP, 1)
    for placeholder, value in {
        "{java}": str(java_executable(game_root)),
        "{target}": str(STAGED),
        "{libraries}": str(libraries),
        "{root}": str(game_root),
        "{cpsep}": ";",
    }.items():
        command = command.replace(placeholder, value)
    if re.search(r"\$\{[A-Za-z_]\w*\}|%[A-Za-z_]\w*%", command):
        raise ValueError("Unexpected unexpanded variable in default dev template.")
    if any(k in command for k in ("{java}", "{root}", "{target}", "{libraries}", "{cpsep}")):
        raise ValueError("Unexpanded NWClient launch placeholder.")
    return command


def main(mode):
    game_root, libraries, staged = validate_files()
    command = make_command(game_root, libraries, staged, mode == "debug")
    if mode == "check":
        print("NWClient offline-dev profile is ready.")
        print("Installation:", game_root)
        print("Runtime Java:", java_executable(game_root))
        print("Java JARs:", len(staged), "loaded directly from workspace/build/dev-artifacts")
        print("No launcher library JARs will be modified.")
        return 0
    print("Starting NWClient offline-dev profile (no account credentials).")
    print("NWClient development JARs are loaded from the workspace; installation is unchanged.")
    if mode == "debug":
        print("Attach a remote Java debugger to 127.0.0.1:5005.")
    try:
        completed = subprocess.run(command, shell=False, cwd=WORKSPACE, check=False)
    except OSError as error:
        raise ValueError(f"Minecraft could not start: {error.strerror}") from None
    return completed.returncode


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("run", "debug", "check"):
        print("Usage: python nwclient_dev.py run|debug|check", file=sys.stderr)
        sys.exit(2)
    try:
        sys.exit(main(sys.argv[1]))
    except ValueError as error:
        print(f"NWClient dev: {error}", file=sys.stderr)
        sys.exit(1)
