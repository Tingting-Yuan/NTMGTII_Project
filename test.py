import subprocess
import time
import socket
import sys
import pytest

from simp_common import (
    MessageType, build_simp_message, parse_simp_message,
    build_client_daemon_message, parse_client_daemon_message,
    DAEMON_PORT, CLIENT_DAEMON_PORT, TIMEOUT
)

DAEMON_ADDR = ("127.0.0.1", DAEMON_PORT)


# ----------------------------------------------------------
# Fixture: 启动 daemon
# ----------------------------------------------------------
@pytest.fixture(scope="function")
def daemon():
    proc = subprocess.Popen([sys.executable, "simp_daemon.py"])
    time.sleep(1.2)

    if proc.poll() is not None:
        pytest.fail("daemon failed to start")

    yield proc

    proc.terminate()
    proc.wait(timeout=1)


# ----------------------------------------------------------
# Helper: 启动 simp_client
# ----------------------------------------------------------
def start_client(username="user"):
    proc = subprocess.Popen(
        [sys.executable, "simp_client.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(0.5)
    proc.stdin.write(username + "\n")
    proc.stdin.flush()
    return proc


# ----------------------------------------------------------
# 1. Test Message Build + Parse
# ----------------------------------------------------------
def test_message_build_parse():
    msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "alice", "hi")
    parsed = parse_simp_message(msg)

    assert parsed["type"] == MessageType.CONTROL.value
    assert parsed["operation"] == 0x02
    assert parsed["username"] == "alice"
    assert parsed["payload"] == "hi"


# ----------------------------------------------------------
# 2. Three-way handshake
# ----------------------------------------------------------
def test_three_way_handshake(daemon):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(TIMEOUT)

    # SYN
    syn = build_simp_message(MessageType.CONTROL, 0x02, 0, "test")
    sock.sendto(syn, DAEMON_ADDR)

    # SYN+ACK
    data, _ = sock.recvfrom(4096)
    parsed = parse_simp_message(data)
    assert parsed["operation"] == 0x06

    # ACK
    ack = build_simp_message(MessageType.CONTROL, 0x04, 0, "test")
    sock.sendto(ack, DAEMON_ADDR)
    sock.close()


# ----------------------------------------------------------
# 3. Stop-and-wait: send 2 chat messages
# ----------------------------------------------------------
def test_stop_and_wait(daemon):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(TIMEOUT)

    # handshake
    sock.sendto(build_simp_message(MessageType.CONTROL, 0x02, 0, "bob"), DAEMON_ADDR)
    sock.recvfrom(4096)
    sock.sendto(build_simp_message(MessageType.CONTROL, 0x04, 0, "bob"), DAEMON_ADDR)

    seq = 0
    for i in range(2):
        sock.sendto(build_simp_message(MessageType.CHAT, 0x01, seq, "bob", f"msg{i}"), DAEMON_ADDR)

        data, _ = sock.recvfrom(4096)
        ack = parse_simp_message(data)

        assert ack["operation"] == 0x04
        assert ack["seq"] == seq
        seq ^= 1

    sock.close()


# ----------------------------------------------------------
# 4. Test simp_client.py minimum behavior:
#    - sends "connect" after username
#    - sends "quit" after user types q
# ----------------------------------------------------------
def test_client_connect_and_quit(daemon):
    # 我们监听一个随机端口，不再使用 7779
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    sock.settimeout(TIMEOUT)

    listening_port = sock.getsockname()[1]

    # 启动 client，并让其知道要把消息发到我们监听的端口
    client = subprocess.Popen(
        [sys.executable, "simp_client.py", str(listening_port)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    time.sleep(0.5)
    client.stdin.write("alice\n")
    client.stdin.flush()

    # 接收 connect
    data, addr = sock.recvfrom(4096)
    msg = parse_client_daemon_message(data.decode())
    assert msg["command"] == "connect"

    # 发送 ok
    sock.sendto(build_client_daemon_message("ok").encode(), addr)

    # 输入 q
    client.stdin.write("q\n")
    client.stdin.flush()

    # 接收 quit
    data, _ = sock.recvfrom(4096)
    msg2 = parse_client_daemon_message(data.decode())
    assert msg2["command"] == "quit"

    client.terminate()
    client.wait(timeout=1)
