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


def port_is_available():
    """Check localhost:5005 without connecting to its single-user JDWP socket."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", PORT))
        except OSError:
            return False
        return True


def same_workspace_java_is_running(game_root):
    """Check PID file against the actual Windows process and Java executable."""
    if not PID_FILE.is_file():
        return False
    try:
        pid = int(PID_FILE.read_text(encoding="ascii").strip())
        if pid <= 0:
            return False

        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD)
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            if kernel32.WaitForSingleObject(handle, 0) != 0x102:  # WAIT_TIMEOUT: alive
                return False
            executable = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(executable))
            if not kernel32.QueryFullProcessImageNameW(
                handle, 0, executable, ctypes.byref(length)
            ):
                return False
            actual_java = os.path.normcase(os.path.abspath(executable.value))
            expected_java = os.path.normcase(str(dev.java_executable(game_root)))
            return actual_java == expected_java
        finally:
            kernel32.CloseHandle(handle)
    except (OSError, ValueError, OverflowError):
        # A missing/stale PID file or inaccessible process is not ownership proof.
        return False


def reuse_existing_debug_jvm(game_root):
    """Return True only for a live JVM launched by this workspace."""
    running = same_workspace_java_is_running(game_root)
    available = port_is_available()

    if running and not available:
        print("Minecraft debug JVM already running from this workspace.")
        print("Reusing JDWP listener at 127.0.0.1:5005 for IntelliJ.")
        return True
    if running and available:
        raise ValueError(
            "The previous Minecraft JVM is still running, but JDWP is not "
            "listening on port 5005. Close Minecraft before starting a new "
            "debug session."
        )
    if not available:
        raise ValueError(
            "JDWP port 5005 is already occupied by another process. Close it "
            "before launching NWClient debugging."
        )
    return False


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
    # F5 may be pressed after the standalone "Start Debug JVM" run. Reuse
    # the same live JVM instead of failing with an occupied JDWP port.
    if reuse_existing_debug_jvm(game_root):
        return 0

    cmd = dev.make_command(game_root, libraries, staged, debug=True)
    if cmd.count(dev.JDWP) != 1:
        raise ValueError("Unexpected Minecraft JVM debugging options.")
    cmd = cmd.replace(dev.JDWP, dev.JDWP.replace("suspend=n", "suspend=y"))
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
