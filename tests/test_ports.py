"""Stopping a previous run: find the listener on a port, stop it, wait until the port is free."""

import os
import socket
import subprocess
import sys
import time

import pytest

from casm import ports

LISTENER: str = (
    "import socket, sys, time\n"
    "s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
    "s.bind(('127.0.0.1', int(sys.argv[1]))); s.listen(); print('up', flush=True); time.sleep(120)\n"
)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def start_listener(port: int) -> subprocess.Popen[str]:
    proc = subprocess.Popen(
        [sys.executable, "-c", LISTENER, str(port)], stdout=subprocess.PIPE, text=True
    )
    assert proc.stdout is not None and proc.stdout.readline().strip() == "up"
    return proc


def test_listening_pids_finds_the_listener_and_nothing_on_a_free_port() -> None:
    port = free_port()
    assert ports.listening_pids(port=port) == []
    proc = start_listener(port)
    try:
        pids = ports.listening_pids(port=port)
        assert (
            pids and os.getpid() not in pids
        )  # on Windows the venv launcher has a child that listens
    finally:
        proc.kill()


def test_free_ports_stops_the_listener_and_the_port_becomes_free() -> None:
    port = free_port()
    proc = start_listener(port)
    stopped = ports.free_ports(host="127.0.0.1", ports=[port])
    assert [p for p, _ in stopped] == [port]
    assert ports.port_is_free(host="127.0.0.1", port=port)
    deadline = time.time() + 10
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    assert proc.poll() is not None, "the old process must have exited"


def test_free_ports_on_free_ports_stops_nothing() -> None:
    assert ports.free_ports(host="127.0.0.1", ports=[free_port(), free_port()]) == []


def test_free_ports_never_stops_the_calling_process() -> None:
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        port = server.getsockname()[1]
        with pytest.raises(RuntimeError, match="still in use"):
            ports.FREE_TIMEOUT_SECONDS = 1.0
            ports.free_ports(host="127.0.0.1", ports=[port])
    ports.FREE_TIMEOUT_SECONDS = 10.0
