import subprocess
import time
import socket
import sys
import pytest
from simp_common import (MessageType, build_simp_message, parse_simp_message, 
                         DAEMON_PORT, CLIENT_DAEMON_PORT, TIMEOUT, 
                         build_client_daemon_message, parse_client_daemon_message)

DAEMON_ADDR = ("127.0.0.1", DAEMON_PORT)

# Pytest fixture for daemon lifecycle
@pytest.fixture(scope="module")
def daemon():
    """Start daemon before tests, stop after all tests complete."""
    print("\n[INFO] Starting simp_daemon.py ...")
    proc = subprocess.Popen([sys.executable, "simp_daemon.py"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # give daemon time to start and bind ports
    yield proc
    print("\n[INFO] Stopping daemon...")
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

def test_message_build_parse():
    """Test message building and parsing (no daemon needed)."""
    print("\n[TEST] Message build + parse")
    msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "alice", "payload")
    parsed = parse_simp_message(msg)
    
    assert parsed["type"] == MessageType.CONTROL.value, "Message type mismatch"
    assert parsed["username"].strip() == "alice", "Username mismatch"
    assert parsed["payload"] == "payload", "Payload mismatch"
    print("PASS: Message header + payload")

def test_three_way_handshake(daemon):
    """Test three-way handshake: SYN -> SYN+ACK -> ACK."""
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
        
        assert parsed["operation"] == (0x02 | 0x04), f"Expected SYN+ACK (0x06), got {parsed['operation']}"
        print("PASS: SYN+ACK received")
        
        # send final ACK
        ack_msg = build_simp_message(MessageType.CONTROL, 0x04, 0, "alice")
        sock.sendto(ack_msg, DAEMON_ADDR)
        time.sleep(0.5)  # give daemon time to process
        
    except socket.timeout:
        pytest.fail("No SYN+ACK received from daemon (timeout)")
    finally:
        # Send FIN to cleanup
        try:
            fin_msg = build_simp_message(MessageType.CONTROL, 0x08, 0, "alice")
            sock.sendto(fin_msg, DAEMON_ADDR)
            time.sleep(0.2)
        except:
            pass
        sock.close()

def test_stop_and_wait(daemon):
    """Test stop-and-wait ARQ with chat messages."""
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
        
        assert parsed["operation"] == (0x02 | 0x04), "Could not establish connection - no SYN+ACK"
        
        # Send ACK to complete handshake
        ack_msg = build_simp_message(MessageType.CONTROL, 0x04, 0, "bob")
        sock.sendto(ack_msg, DAEMON_ADDR)
        time.sleep(0.5)
    except socket.timeout:
        pytest.fail("Could not establish connection - timeout")
    
    # Now test stop-and-wait with chat messages
    try:
        for i in range(2):
            msg = build_simp_message(MessageType.CHAT, 0x01, seq, "bob", f"msg{i}")
            sock.sendto(msg, DAEMON_ADDR)
            
            # Receive ACK
            data, _ = sock.recvfrom(4096)
            parsed = parse_simp_message(data)
            
            assert parsed["type"] == MessageType.CONTROL.value, f"Expected CONTROL message, got type {parsed['type']}"
            assert parsed["operation"] == 0x04, f"Expected ACK (0x04), got {parsed['operation']}"
            assert parsed["seq"] == seq, f"Expected seq={seq}, got seq={parsed['seq']}"
            
            print(f"PASS: Message {i} acknowledged with seq={seq}")
            seq = 1 - seq
            
    except socket.timeout:
        pytest.fail(f"No ACK received for seq={seq}")
    finally:
        # Send FIN to cleanup
        try:
            fin_msg = build_simp_message(MessageType.CONTROL, 0x08, 0, "bob")
            sock.sendto(fin_msg, DAEMON_ADDR)
            # Wait for FIN ACK
            sock.recvfrom(4096)
        except:
            pass
        sock.close()

def test_daemon_client_communication(daemon):
    """Test client-daemon internal protocol."""
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
        
        assert response['command'] == 'ok', f"Expected 'ok', got '{response['command']}'"
        print("PASS: Client connected to daemon successfully")
            
    except socket.timeout:
        pytest.fail("No response from daemon (timeout)")
    except Exception as e:
        pytest.fail(f"Error during test: {e}")
    finally:
        test_sock.close()

if __name__ == "__main__":
    # Allow running directly with python (will use pytest)
    pytest.main([__file__, "-v", "-s"])
