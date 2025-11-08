import pytest
from simp_common import *
from simp_server import SimpDaemon


#############################
#   Test: Message Format    #
#############################

class TestMessageFormat:
    """Test only message format (header + payload)"""

    def test_build_message(self):
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            1,
            "alice",
            "Hello"
        )
        assert msg[0] == MessageType.CHAT.value
        assert msg[1] == OperationType.CHAT_MSG.value
        assert msg[2] == 1
        assert msg[3] == "alice"
        # assert len(msg) == HEADER_SIZE + len("Hello")

    def test_parse_message(self):
        original = "TestPayload"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            0,
            "bob",
            original
        )
        parsed = parse_simp_message(msg)
        assert parsed["type"] == MessageType.CONTROL.value
        assert parsed["operation"] == OperationType.ACK.value
        assert parsed["payload"] == original


#############################
#   Test: Three-way HS      #
#############################

class TestThreeWayHandshake:
    """Test simplified three-way handshake"""

    def test_syn(self):
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "alice",
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed["operation"] == OperationType.SYN.value

    def test_syn_ack(self):
        syn_ack_val = OperationType.SYN.value | OperationType.ACK.value
        msg = build_simp_message(
            MessageType.CONTROL,
            syn_ack_val,
            0,
            "server",
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed["operation"] == (OperationType.SYN.value | OperationType.ACK.value)

    def test_ack(self):
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            1,
            "alice",
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed["operation"] == OperationType.ACK.value


#############################
#   Test: Stop & Wait       #
#############################

class TestStopAndWait:
    """Test simple stop-and-wait sequence checking"""

    def test_toggle_sequence(self):
        seq = 0
        for i in range(6):
            assert seq == (i % 2)
            seq = 1 - seq

    def test_message_ack_pair(self):
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "alice",
            "Hi"
        )
        ack = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            0,
            "server",
            ""
        )
        parsed_msg = parse_simp_message(msg)
        parsed_ack = parse_simp_message(ack)

        assert parsed_msg["seq"] == parsed_ack["seq"] == 0


#########################################
#   Test: Daemon-client communication   #
#########################################

class TestDaemonClientMessage:
    """Test client-daemon message building and parsing"""

    def test_build_connect(self):
        msg = build_client_daemon_message("connect", username="alice")
        assert "connect" in msg
        assert "username=alice" in msg

    def test_parse_connect(self):
        msg = build_client_daemon_message("connect", username="bob")
        parsed = parse_client_daemon_message(msg)
        assert parsed["command"] == "connect"
        assert parsed["username"] == "bob"


#########################################
# Run with python test.py
#########################################

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
