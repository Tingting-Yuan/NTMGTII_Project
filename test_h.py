import subprocess
import time
import socket
import sys
import pytest
from simp_common import (MessageType, build_simp_message, parse_simp_message, 
                         DAEMON_PORT, CLIENT_DAEMON_PORT, TIMEOUT, 
                         build_client_daemon_message, parse_client_daemon_message)

DAEMON_ADDR = ("127.0.0.1", DAEMON_PORT)

def start_client(username="testuser"):
    """Starts the simp_client process."""
    print(f"\n[INFO] Starting simp_client.py for user {username}...")
    # Use Popen to control stdin/stdout for interaction
    proc = subprocess.Popen([sys.executable, "simp_client.py"], 
                            stdin=subprocess.PIPE, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            text=True)
    time.sleep(1)
    # The client immediately prompts for a username
    proc.stdin.write(f"{username}\n")
    proc.stdin.flush()
    return proc

# --- DAEMON FIXTURE (scope="function" to avoid port conflict) ---
@pytest.fixture(scope="function") 
def daemon():
    """Start daemon before tests, stop after each test completes, ensuring ports are freed."""
    print("\n[INFO] Starting simp_daemon.py ...")
    proc = subprocess.Popen([sys.executable, "simp_daemon.py"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1.5)  # Give daemon time to start and bind ports
    
    # Check if the daemon failed to start
    if proc.poll() is not None:
         stdout, stderr = proc.communicate(timeout=0.1)
         pytest.fail(f"Daemon failed to start. STDOUT: {stdout.strip()}. STDERR: {stderr.strip()}")
        
    yield proc
    print("\n[INFO] Stopping daemon...")
    proc.terminate()
    try:
        proc.wait(timeout=1) 
    except subprocess.TimeoutExpired:
        proc.kill()

# --- CLIENT TESTING FIXTURE ---
@pytest.fixture
def client_conn_setup():
    """
    Set up a temporary UDP socket that acts as the DAEMON's client-daemon listener.
    It binds to CLIENT_DAEMON_PORT (7779) to intercept messages from the client process.
    """
    print(f"\n[INFO] Setting up temporary socket on port {CLIENT_DAEMON_PORT} to intercept client messages...")
    temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        # Bind to CLIENT_DAEMON_PORT to intercept client messages
        temp_sock.bind(("127.0.0.1", CLIENT_DAEMON_PORT))
    except OSError as e:
        pytest.fail(f"Failed: Could not bind to port {CLIENT_DAEMON_PORT}. Ensure no other daemon/test is running.")
        
    temp_sock.settimeout(TIMEOUT)
    yield temp_sock
    temp_sock.close()

# --- UTILITY FUNCTION FOR CLIENT TESTS ---
def run_client_action_test(client_proc, expected_command, input_sequence, temp_sock):
    """Utility function to drive client input and check daemon-side message."""
    
    # 1. Send all required input to client's stdin
    for input_line in input_sequence:
        client_proc.stdin.write(f"{input_line}\n")
    client_proc.stdin.flush()
    # Wait for the client to process input and send the message
    time.sleep(1) 

    # 2. Check for the expected message on the temporary daemon socket
    try:
        data, addr = temp_sock.recvfrom(4096)
        msg = parse_client_daemon_message(data.decode('ascii'))
        
        assert msg['command'] == expected_command, f"Expected command '{expected_command}', got '{msg['command']}'"
        print(f"PASS: Client sent expected '{expected_command}' command.")
        
        # 3. Respond with an 'ok' to keep the client from hanging if it expects one
        response = build_client_daemon_message('ok')
        temp_sock.sendto(response.encode('ascii'), addr)
        
        return addr # Return the client's address for subsequent communication
        
    except socket.timeout:
        pytest.fail(f"Client failed to send '{expected_command}' message (timeout)")
    except Exception as e:
        pytest.fail(f"Error during client action test: {e}")


# =========================================================================
# === DAEMON PROTOCOL TESTS ===
# =========================================================================

def test_message_build_parse_no_daemon():
    """Test message building and parsing (no daemon needed)."""
    print("\n[TEST] Message build + parse")
    msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "alice", "payload")
    parsed = parse_simp_message(msg)
    
    assert parsed["type"] == MessageType.CONTROL.value, "Message type mismatch"
    assert parsed["username"].strip() == "alice", "Username mismatch"
    assert parsed["payload"] == "payload", "Payload mismatch"
    print("PASS: Message header + payload")

def test_three_way_handshake_with_daemon(daemon):
    """Test three-way handshake: SYN -> SYN+ACK -> ACK. (Requires daemon)"""
    print("\n[TEST] Three-way handshake: SYN -> SYN+ACK -> ACK")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    sock.settimeout(TIMEOUT)
    try:
        # 1. send SYN
        syn_msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "alice")
        sock.sendto(syn_msg, DAEMON_ADDR)

        # 2. Receive SYN+ACK
        data, _ = sock.recvfrom(4096)
        parsed = parse_simp_message(data)
        
        assert parsed["operation"] == (0x02 | 0x04), f"Expected SYN+ACK (0x06), got {parsed['operation']}"
        print("PASS: SYN+ACK received")
        
        # 3. Send final ACK
        ack_msg = build_simp_message(MessageType.CONTROL, 0x04, 0, "alice")
        sock.sendto(ack_msg, DAEMON_ADDR)
        time.sleep(0.5)
        
    except socket.timeout:
        pytest.fail("No SYN+ACK received from daemon (timeout)")
    finally:
        # Send FIN to cleanup
        try:
            fin_msg = build_simp_message(MessageType.CONTROL, 0x08, 0, "alice")
            sock.sendto(fin_msg, DAEMON_ADDR)
            sock.recvfrom(4096)
        except:
            pass
        sock.close()

def test_stop_and_wait_with_daemon(daemon):
    """Test stop-and-wait ARQ with chat messages. (Requires daemon)"""
    print("\n[TEST] Stop-and-wait message")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 0))
    sock.settimeout(TIMEOUT)
    seq = 0
    
    # Establish connection
    try:
        syn_msg = build_simp_message(MessageType.CONTROL, 0x02, 0, "bob")
        sock.sendto(syn_msg, DAEMON_ADDR)
        data, _ = sock.recvfrom(4096)
        ack_msg = build_simp_message(MessageType.CONTROL, 0x04, 0, "bob")
        sock.sendto(ack_msg, DAEMON_ADDR)
        time.sleep(0.5)
    except:
        pytest.fail("Could not establish connection for stop-and-wait test.")
    
    # Test stop-and-wait
    try:
        for i in range(2):
            msg = build_simp_message(MessageType.CHAT, 0x01, seq, "bob", f"msg{i}")
            sock.sendto(msg, DAEMON_ADDR)
            
            # Receive ACK
            data, _ = sock.recvfrom(4096)
            parsed = parse_simp_message(data)
            
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
            sock.recvfrom(4096)
        except:
            pass
        sock.close()

def test_daemon_client_communication_with_daemon(daemon):
    """Test the daemon's response to the initial 'connect' command. (Requires daemon)"""
    print("\n[TEST] Daemon-client communication (Connect command)")
    
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_sock.bind(('', 0))
    test_sock.settimeout(TIMEOUT)
    
    try:
        # Send connect message to daemon
        connect_msg = build_client_daemon_message('connect', username='tester')
        test_sock.sendto(connect_msg.encode('ascii'), ("127.0.0.1", CLIENT_DAEMON_PORT))
        
        # Wait for OK response from the actual daemon
        data, _ = test_sock.recvfrom(4096)
        response = parse_client_daemon_message(data.decode('ascii'))
        
        assert response['command'] == 'ok', f"Expected 'ok', got '{response['command']}'"
        print("PASS: Daemon responded with 'ok'")
            
    except socket.timeout:
        pytest.fail("No response from daemon (timeout)")
    finally:
        test_sock.close()

# =======================================================================
# === CLIENT INTERACTION TESTS ===
# =======================================================================

def test_client_connect_command(client_conn_setup):
    """Test client sends 'connect' after username input."""
    print("\n[TEST] Client: Connect (Username input)")
    temp_sock = client_conn_setup
    username = "testuser"
    
    # Start client (will send username and then 'connect' command)
    client_proc = start_client(username=username) 

    try:
        # The client automatically sends 'connect'
        run_client_action_test(client_proc, 'connect', [], temp_sock)
        
    finally:
        client_proc.terminate()
        client_proc.wait(timeout=1)


def test_client_invite_and_send(client_conn_setup):
    """Test client's 'invite' and 'send' message functionality."""
    print("\n[TEST] Client: Invite and Send")
    temp_sock = client_conn_setup
    username = "testuser_invite"
    
    client_proc = start_client(username=username) 
    
    try:
        # 1. Handle initial 'connect' command (client is now in idle_mode, blocked on input)
        client_addr = run_client_action_test(client_proc, 'connect', [], temp_sock)
        
        # 2. Drive client to send 'invite' command: [1] (Start chat) -> [127.0.0.2] (Target IP)
        # Client is now blocked again on "Enter choice:" input in idle_mode.
        input_sequence_invite = ['1', '127.0.0.2']
        run_client_action_test(client_proc, 'invite', input_sequence_invite, temp_sock)
        
        # 3. Simulate daemon sending 'connected' to client to change state
        connected_msg = build_client_daemon_message('connected', username='remote_user')
        
        if not client_addr:
             pytest.fail("Client address not captured for simulation")

        temp_sock.sendto(connected_msg.encode('ascii'), client_addr)
        time.sleep(0.5) # Wait for client's listener thread to receive the message

        # --- CRITICAL FIX: Inject commands in a sequence to switch modes and send message ---
        # The client is currently blocked on 'Enter choice:' in idle_mode.
        # Sending a newline breaks idle_mode's input().
        # The client detects self.in_chat=True, enters chat_mode, and blocks on chat input.
        # The next input is the message payload.
        
        # We need to explicitly break the blocking input and then send the chat message
        
        client_proc.stdin.write('\n')
        client_proc.stdin.flush()
        time.sleep(1) # Wait for client to exit idle_mode and enter chat_mode
        
        # 4. Drive client to send 'send' command: [test message]
        input_sequence_send = ['test message']
        run_client_action_test(client_proc, 'send', input_sequence_send, temp_sock)
        
    finally:
        # Clean up: Send 'q' to quit chat and 'q' to quit client from idle mode
        client_proc.stdin.write('q\nq\n')
        client_proc.stdin.flush()
        client_proc.terminate()
        client_proc.wait(timeout=1)


def test_client_quit_chat(client_conn_setup):
    """Test client's ability to quit the chat."""
    print("\n[TEST] Client: Quit Chat")
    temp_sock = client_conn_setup
    username = "testuser_quit"
    
    client_proc = start_client(username=username)
    
    try:
        # 1. Handle initial 'connect' command
        client_addr = run_client_action_test(client_proc, 'connect', [], temp_sock)

        # 2. Simulate connection being established (client is now in chat_mode)
        connected_msg = build_client_daemon_message('connected', username='remote_user')
        
        if not client_addr:
             pytest.fail("Client address not captured for simulation")

        temp_sock.sendto(connected_msg.encode('ascii'), client_addr)
        time.sleep(0.5) # Wait for client's listener thread to receive the message
        
        # --- CRITICAL FIX ---
        # Unblock the client's current input() call
        client_proc.stdin.write('\n')
        client_proc.stdin.flush()
        time.sleep(1) # Wait for client to enter chat_mode
        # --- CRITICAL FIX END ---

        # 3. Drive client to send 'quit' command: [q] (Quit chat)
        input_sequence_quit = ['q']
        run_client_action_test(client_proc, 'quit', input_sequence_quit, temp_sock)
        
    finally:
        # Clean up: Send 'q' to quit client from idle mode
        client_proc.stdin.write('q\n') 
        client_proc.stdin.flush()
        client_proc.terminate()
        client_proc.wait(timeout=1)
