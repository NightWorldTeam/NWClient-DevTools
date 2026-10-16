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


def path_from_setting(value):
    """Resolve an explicit Windows path or a relative path from the workspace."""
    expanded = os.path.expandvars(os.path.expanduser(str(value).strip().strip('"')))
    path = Path(expanded)
    return (path if path.is_absolute() else WORKSPACE / path).resolve()


def missing_installation_files(game_root):
    """A directory alone is not a usable Minecraft installation."""
    required = {
        "libraries": game_root / "libraries",
        "assets": game_root / "assets",
        "Minecraft 1.20 client.jar":
            game_root / "instances" / "nwclient dev" / "version" / "client.jar",
    }
    return [label for label, location in required.items() if not location.exists()]


def read_deploy_root():
    """Use deploy.toml ONLY for installation paths, never session credentials."""
    config_file = WORKSPACE / "deploy.toml"
    if not config_file.is_file():
        raise ValueError(
            "No usable NWLauncher installation found via NWCLIENT_HOME or "
            "%APPDATA%/.lexplosion. Create deploy.toml in the workspace and "
            "set [launch].root to your game files directory "
            "(or provide [launch].libraries / target)."
        )
    try:
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib
        with config_file.open("rb") as stream:
            config = tomllib.load(stream)
    except (OSError, ValueError) as error:
        raise ValueError(
            "deploy.toml could not be read. Check its TOML syntax and paths."
        ) from None
    launch = config.get("launch", {})
    if not isinstance(launch, dict):
        raise ValueError("deploy.toml [launch] must be a TOML table.")

    raw_root = launch.get("root") or config.get("root")
    raw_libraries = launch.get("libraries") or config.get("libraries")
    raw_target = config.get("target")
    libraries = path_from_setting(raw_libraries) if raw_libraries else None
    target = path_from_setting(raw_target) if raw_target else None

    if raw_root:
        game_root = path_from_setting(raw_root)
    elif libraries:
        game_root = libraries.parent
    elif target:
        if [part.lower() for part in target.parts[-3:]] != [
            "libraries", "org", "nightworld"
        ]:
            raise ValueError(
                "deploy.toml target must end with libraries/org/nightworld "
                "if [launch].root and [launch].libraries are omitted."
            )
        game_root = target.parents[2]
    else:
        # A deploy.toml file can contain deployment rules, launch flags or
        # other settings without specifying an installation directory.
        # It still takes precedence; unspecified paths use the normal
        # NWLauncher installation instead of failing on missing keys.
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise ValueError(
                "deploy.toml has no installation path and APPDATA is not set. "
                "Set [launch].root, [launch].libraries, or target."
            )
        game_root = path_from_setting(appdata) / ".lexplosion"

    if libraries and os.path.normcase(str(libraries)) != os.path.normcase(
        str(game_root / "libraries")
    ):
        raise ValueError(
            "deploy.toml [launch].root and [launch].libraries point to "
            "different installations."
        )
    if target and os.path.normcase(str(target)) != os.path.normcase(
        str(game_root / "libraries" / "org" / "nightworld")
    ):
        raise ValueError(
            "deploy.toml target must equal <root>/libraries/org/nightworld."
        )
    return game_root


def locate_installation():
    """Priority: deploy.toml (authoritative) > NWCLIENT_HOME > APPDATA."""
    config_file = WORKSPACE / "deploy.toml"

    # An explicit local config always wins. If invalid, stop rather than
    # silently running another Minecraft installation or ignoring mistakes.
    if config_file.exists():
        if not config_file.is_file():
            raise ValueError("deploy.toml exists but is not a readable file.")
        root = read_deploy_root()
        missing = missing_installation_files(root)
        if missing:
            raise ValueError(
                "deploy.toml takes priority, but its installation is incomplete "
                "(missing: " + ", ".join(missing)
                + "). Fix deploy.toml or remove it to enable autodetection."
            )
        return root, "deploy.toml"

    custom = os.environ.get("NWCLIENT_HOME")
    if custom and custom.strip():
        root = path_from_setting(custom)
        if not missing_installation_files(root):
            return root, "NWCLIENT_HOME"
        print("NWCLIENT_HOME does not contain a complete NWClient dev profile; trying APPDATA.")

    appdata = os.environ.get("APPDATA")
    if appdata:
        root = path_from_setting(appdata) / ".lexplosion"
        if not missing_installation_files(root):
            return root, "%APPDATA%/.lexplosion"

    raise ValueError(
        "No usable NWLauncher installation found in NWCLIENT_HOME or "
        "%APPDATA%/.lexplosion. Create deploy.toml and set [launch].root "
        "to the directory containing libraries, assets, and instances."
    )


def validate_files():
    if os.name != "nt":
        raise ValueError("The existing NWClient Vanilla dev profile requires Windows.")
    game_root, source = locate_installation()
    libraries = game_root / "libraries"
    if not TEMPLATE.is_file():
        raise ValueError("Default dev-launch-template.txt is missing.")

    staged = []
    for directory in DEV_JARS:
        files = sorted((STAGED / directory).glob("*.jar"))
        if len(files) != 1:
            raise ValueError(
                f"Expected one staged JAR in build/dev-artifacts/{directory}, "
                f"found {len(files)}. Run devPrepare first."
            )
        staged.append(files[0])
    return game_root, libraries, staged, source


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
    # Enable live XAML source overrides only for this development workspace.
    # The JVM property is consumed by MinecraftApi.XamlView on the game thread.
    xaml_option = '-Dnwclient.xaml.dir="' + str(WORKSPACE) + '"'
    if ' -cp "' not in command:
        raise ValueError("Cannot locate JVM classpath in dev launch template.")
    command = command.replace(' -cp "', ' ' + xaml_option + ' -cp "', 1)
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
    game_root, libraries, staged, source = validate_files()
    command = make_command(game_root, libraries, staged, mode == "debug")
    if mode == "check":
        print("NWClient offline-dev profile is ready.")
        print("Installation:", game_root, "(from", source + ")")
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
