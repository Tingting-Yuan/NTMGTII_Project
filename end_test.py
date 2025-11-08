#!/usr/bin/env python3
import subprocess
import time
import socket
import sys
from simp_common import MessageType, build_simp_message, parse_simp_message, DAEMON_PORT, CLIENT_DAEMON_PORT, TIMEOUT, Test_PORT

DAEMON_ADDR = ("127.0.0.1", DAEMON_PORT)

def start_daemon():
    print("[INFO] Starting simp_daemon.py ...")
    proc = subprocess.Popen([sys.executable, "simp_daemon.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)  # give daemon time to start
    return proc

def start_client(username="testuser"):
    print("[INFO] Starting simp_client.py ...")
    proc = subprocess.Popen([sys.executable, "simp_client.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(1)
    # send username to client stdin
    proc.stdin.write(f"{username}\n")
    proc.stdin.flush()
    return proc

def test_message_build_parse():
    print("\n[TEST] Message build + parse")
    msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "alice", "payload")
    parsed = parse_simp_message(msg)
    if parsed["type"] == MessageType.CONTROL.value and parsed["username"].strip() == "alice" and parsed["payload"] == "payload":
        print("PASS: Message header + payload")
        return True
    print("FAIL: Message build/parse")
    return False

def test_three_way_handshake():
    print("\n[TEST] Three-way handshake: SYN -> SYN+ACK -> ACK")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', Test_PORT))  # random client port
    sock.settimeout(TIMEOUT)
    try:
        # send SYN
        syn_msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "alice")
        sock.sendto(syn_msg, DAEMON_ADDR)

        data, _ = sock.recvfrom(4096)
        parsed = parse_simp_message(data)
        if parsed["operation"] == (0x02 | 0x04):
            print("PASS: SYN+ACK received")
            # send final ACK
            ack_msg = build_simp_message(MessageType.CONTROL, 0x04, 0, "alice")
            sock.sendto(ack_msg, DAEMON_ADDR)
            return True
        else:
            print("FAIL: Wrong response:", parsed)
            return False
    except socket.timeout:
        print("FAIL: No SYN+ACK from daemon")
        return False
    finally:
        sock.close()

def test_stop_and_wait():
    print("\n[TEST] Stop-and-wait message")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    sock.settimeout(TIMEOUT)
    seq = 0
    try:
        for i in range(2):
            msg = build_simp_message(MessageType.CHAT, 0x01, seq, "alice", f"msg{i}")
            sock.sendto(msg, DAEMON_ADDR)
            data, _ = sock.recvfrom(4096)
            parsed = parse_simp_message(data)
            if parsed["operation"] != 0x04 or parsed["seq"] != seq:
                print(f"FAIL: Wrong ACK for seq={seq}")
                return False
            print(f"PASS: Message {i} acknowledged with seq={seq}")
            seq = 1 - seq
        return True
    except socket.timeout:
        print(f"FAIL: No ACK for seq={seq}")
        return False
    finally:
        sock.close()

def test_daemon_client_communication():
    print("\n[TEST] Daemon-client communication")
    client = start_client("tester")
    time.sleep(1)  # wait for client to connect
    out = client.stdout.read()
    if "Connected" in out or "connected" in out:
        print("PASS: Client connected to daemon")
        client.terminate()
        return True
    else:
        print("FAIL: Daemon did not respond")
        client.terminate()
        return False

if __name__ == "__main__":
    daemon_proc = start_daemon()
    try:
        results = [
            test_message_build_parse(),
            test_three_way_handshake(),
            test_stop_and_wait(),
            test_daemon_client_communication()
        ]
        print("\n============== SUMMARY ==============")
        if all(results):
            print("ALL TESTS PASSED")
        else:
            print("SOME TESTS FAILED")
    finally:
        daemon_proc.terminate()
