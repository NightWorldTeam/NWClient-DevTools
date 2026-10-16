#!/usr/bin/env python3
"""Start the local Minecraft JVM suspended for IntelliJ remote debugging.

This command is a short-lived Gradle prelaunch task: it returns when the JDWP
listener is ready. The Minecraft process stays alive independently of Gradle.
"""
import os
import socket
import subprocess
import sys
import time

import nwclient_dev as dev

PORT = 5005
READY_MESSAGE = "Listening for transport dt_socket at address"
TIMEOUT_SECONDS = 30
LOG_FILE = dev.WORKSPACE / "build" / "dev-logs" / "minecraft-debug.log"
PID_FILE = dev.WORKSPACE / "build" / "dev-logs" / "minecraft-debug.pid"


def ensure_port_available():
    # Never connect to JDWP for readiness probing: some JVMs accept only
    # one debugger connection and a probe would consume it.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", PORT))
        except OSError:
            raise ValueError(
                "JDWP port 5005 is occupied. Close the previous Minecraft "
                "debug session before launching another."
            ) from None


def await_ready(process):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if LOG_FILE.is_file():
            stdout = LOG_FILE.read_text(encoding="utf-8", errors="replace")
            if READY_MESSAGE in stdout:
                return
        if process.poll() is not None:
            raise ValueError(
                "Minecraft JVM exited before opening JDWP. "
                "See build/dev-logs/minecraft-debug.log."
            )
        time.sleep(0.15)
    if process.poll() is None:
        process.terminate()
    raise ValueError(
        "JDWP did not become ready after 30 seconds. "
        "See build/dev-logs/minecraft-debug.log."
    )


def start():
    if os.name != "nt":
        raise ValueError("This launcher currently requires Windows.")
    game_root, libraries, staged, source = dev.validate_files()
    cmd = dev.make_command(game_root, libraries, staged, debug=True)

    if cmd.count(dev.JDWP) != 1:
        raise ValueError("Unexpected Minecraft JVM debugging options.")
    cmd = cmd.replace(dev.JDWP, dev.JDWP.replace("suspend=n", "suspend=y"))
    ensure_port_available()
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    with LOG_FILE.open("wb") as log:
        process = subprocess.Popen(
            cmd,
            shell=False,
            cwd=str(dev.WORKSPACE),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    try:
        await_ready(process)
    except BaseException:
        if process.poll() is None:
            process.terminate()
        raise
    PID_FILE.write_text(str(process.pid), encoding="ascii")
    print("Minecraft JVM waiting for IntelliJ debugger on 127.0.0.1:5005")
    print("Installation:", game_root, "(from", source + ")")
    print("Minecraft output:", LOG_FILE)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(start())
    except (ValueError, OSError) as err:
        print("NWClient IntelliJ debug:", err, file=sys.stderr)
        sys.exit(1)
