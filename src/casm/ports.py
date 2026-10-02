"""Finds and stops processes already listening on a port, so a launch always replaces a previous run."""

import os
import signal
import socket
import subprocess
import sys
import time

FREE_TIMEOUT_SECONDS: float = 10.0


def listening_pids(*, port: int) -> list[int]:
    """The process ids listening on a TCP port (stdlib only: netstat on Windows, lsof elsewhere)."""
    if sys.platform == "win32":
        output: str = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False
        ).stdout
        pids: set[int] = set()
        for line in output.splitlines():
            parts: list[str] = line.split()
            if (
                len(parts) >= 5
                and parts[0] == "TCP"
                and parts[3] == "LISTENING"
                and parts[1].rsplit(":", 1)[-1] == str(port)
            ):
                pids.add(int(parts[4]))
        return sorted(pids)
    result = subprocess.run(
        ["lsof", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
        check=False,
    )
    return sorted({int(token) for token in result.stdout.split()})


def stop_pid(*, pid: int) -> None:
    """Stop a process and its children."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False
        )
        return
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        os.kill(pid, signal.SIGKILL)  # still alive after the grace period
    except ProcessLookupError:
        pass


def port_is_free(*, host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        return probe.connect_ex((host, port)) != 0


def free_ports(*, host: str, ports: list[int]) -> list[tuple[int, int]]:
    """Stop whatever listens on each port (never this process), then wait until the ports are free.

    Args:
        host: The address the ports are probed on.
        ports: The ports a launch needs.

    Returns:
        (port, pid) for every process that was stopped.

    Raises:
        RuntimeError: If a port is still in use after the processes were stopped.
    """
    stopped: list[tuple[int, int]] = []
    for port in ports:
        for pid in listening_pids(port=port):
            if pid != os.getpid():
                stop_pid(pid=pid)
                stopped.append((port, pid))
    deadline: float = time.time() + FREE_TIMEOUT_SECONDS
    for port in ports:
        while not port_is_free(host=host, port=port):
            if time.time() > deadline:
                raise RuntimeError(
                    f"Port {port} is still in use after stopping its process; free it and run again."
                )
            time.sleep(0.2)
    return stopped
