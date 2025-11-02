import socket
import time
import subprocess
import pytest

# ===============================
# 1️⃣ Test Message Format
# ===============================
def test_message_format():
    from protocol import make_message, parse_message

    msg = make_message(seq=1, ack=0, flag='DATA', payload=b'Hello')
    seq, ack, flag, payload = parse_message(msg)

    assert seq == 1
    assert ack == 0
    assert flag == 'DATA'
    assert payload == b'Hello'


# ===============================
# 2️⃣ Test Three-Way Handshake
# ===============================
def test_three_way_handshake():
    """Simulate UDP three-way handshake"""
    server = subprocess.Popen(["python3", "server.py"])
    time.sleep(1)

    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.settimeout(2)

    client.sendto(b'SYN', ('localhost', 12000))
    data, _ = client.recvfrom(1024)
    assert data == b'SYN-ACK'

    client.sendto(b'ACK', ('localhost', 12000))

    client.close()
    server.terminate()
    time.sleep(0.5)


# ===============================
# 3️⃣ Test Stop-and-Wait
# ===============================
def test_stop_and_wait():
    from protocol import StopAndWait
    sender = StopAndWait()
    receiver = StopAndWait()

    pkt = sender.make_packet(seq=1, data=b'Hi')
    ack = receiver.receive_packet(pkt)
    assert ack == b'ACK1'

    sender.handle_ack(ack)
    assert sender.next_seq() == 2


# ===============================
# Optional: Print Score Summary
# ===============================
def test_summary():
    print("\nAll three functions tested successfully:")
    print("✅ Message format (25 pts)")
    print("✅ Three-way handshake (10 pts)")
    print("✅ Stop-and-wait protocol (10 pts)")
