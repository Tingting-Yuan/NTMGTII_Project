import subprocess
import time
import socket
import sys
from simp_common import MessageType, build_simp_message, parse_simp_message, DAEMON_PORT, CLIENT_DAEMON_PORT, TIMEOUT, Test_PORT, build_client_daemon_message, parse_client_daemon_message

DAEMON_ADDR = ("127.0.0.1", DAEMON_PORT)

def start_daemon():
    print("[INFO] Starting simp_daemon.py ...")
    proc = subprocess.Popen([sys.executable, "simp_daemon.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # give daemon more time to start and bind ports
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
    sock.bind(('', 0))  # bind to random available port
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
            time.sleep(0.5)  # give daemon time to process
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
    
    # First establish connection
    try:
        syn_msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "bob")
        sock.sendto(syn_msg, DAEMON_ADDR)
        data, _ = sock.recvfrom(4096)
        parsed = parse_simp_message(data)
        if parsed["operation"] != (0x02 | 0x04):
            print("FAIL: Could not establish connection")
            return False
        # Send ACK to complete handshake
        ack_msg = build_simp_message(MessageType.CONTROL, 0x04, 0, "bob")
        sock.sendto(ack_msg, DAEMON_ADDR)
        time.sleep(0.5)
    except socket.timeout:
        print("FAIL: Could not establish connection")
        return False
    
    # Now test stop-and-wait with chat messages
    try:
        for i in range(2):
            msg = build_simp_message(MessageType.CHAT, 0x01, seq, "bob", f"msg{i}")
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
        # Send FIN to cleanup
        fin_msg = build_simp_message(MessageType.CONTROL, 0x08, 0, "bob")
        sock.sendto(fin_msg, DAEMON_ADDR)
        sock.close()

def test_daemon_client_communication():
    print("\n[TEST] Daemon-client communication")
    
    # Create a direct socket to test client-daemon protocol
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_sock.bind(('', 0))  # bind to random port
    test_sock.settimeout(TIMEOUT)
    
    try:
        # Send connect message to daemon
        connect_msg = build_client_daemon_message('connect', username='tester')
        test_sock.sendto(connect_msg.encode('ascii'), ("127.0.0.1", CLIENT_DAEMON_PORT))
        
        # Wait for OK response
        data, _ = test_sock.recvfrom(4096)
        response = parse_client_daemon_message(data.decode('ascii'))
        
        if response['command'] == 'ok':
            print("PASS: Client connected to daemon successfully")
            return True
        else:
            print(f"FAIL: Unexpected response: {response}")
            return False
            
    except socket.timeout:
        print("FAIL: No response from daemon")
        return False
    except Exception as e:
        print(f"FAIL: Error during test: {e}")
        return False
    finally:
        test_sock.close()

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
            for i, result in enumerate(results, 1):
                status = "✓ PASS" if result else "✗ FAIL"
                print(f"  Test {i}: {status}")
    finally:
        print("\n[INFO] Stopping daemon...")
        daemon_proc.terminate()
        daemon_proc.wait(timeout=2)
