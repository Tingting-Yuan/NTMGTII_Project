import pytest
from simp_common import *
from simp_daemon import SimpDaemon


#############################
#   1. Message Format Tests
#############################

class TestMessageFormat:
    def test_header_fields(self):
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            1,
            "alice",
            "Hallo, welcome to IMC simp!"
        )
        parsed = parse_simp_message(msg)
        assert parsed["type"] == MessageType.CONTROL.value
        assert parsed["operation"] == OperationType.SYN.value
        assert parsed["seq"] == 1
        assert parsed["username"] == "alice"
        assert parsed["length"] == len("Hallo, welcome to IMC simp!")
        assert parsed["payload"] == "Hallo, welcome to IMC simp!"

    def test_chat_message_op(self):
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "Bob",
            "Hallo!"
        )
        parsed = parse_simp_message(msg)
        assert parsed["type"] == MessageType.CHAT.value
        assert parsed["operation"] == OperationType.CHAT_MSG.value


#############################
#   2. Control Operations
#############################

class TestControlOps:
    def test_syn(self):
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "a",
            ""
        )
        assert parse_simp_message(msg)["operation"] == OperationType.SYN.value

    def test_syn_ack(self):
        op = OperationType.SYN.value | OperationType.ACK.value
        msg = build_simp_message(
            MessageType.CONTROL,
            op,
            0,
            "daemon",
            ""
        )
        assert parse_simp_message(msg)["operation"] == op

    def test_fin(self):
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            1,
            "x",
            ""
        )
        assert parse_simp_message(msg)["operation"] == OperationType.FIN.value


#############################
#   3. Three-way Handshake
#############################

class TestHandshake:
    def test_three_way(self):
        syn = build_simp_message(
            MessageType.CONTROL, OperationType.SYN.value, 0, "u", ""
        )
        parsed_syn = parse_simp_message(syn)
        assert parsed_syn["operation"] == OperationType.SYN.value

        syn_ack = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value | OperationType.ACK.value,
            0,
            "server",
            ""
        )
        parsed_syn_ack = parse_simp_message(syn_ack)
        assert parsed_syn_ack["operation"] == (OperationType.SYN.value | OperationType.ACK.value)

        ack = build_simp_message(
            MessageType.CONTROL, OperationType.ACK.value, 1, "u", ""
        )
        parsed_ack = parse_simp_message(ack)
        assert parsed_ack["operation"] == OperationType.ACK.value


#############################
#   4. Stop-and-Wait
#############################

class TestStopAndWait:
    def test_seq_toggle(self):
        seq = 0
        for _ in range(10):
            seq = 1 - seq
        assert seq in (0, 1)

    def test_message_ack_pair(self):
        msg = build_simp_message(
            MessageType.CHAT, OperationType.CHAT_MSG.value, 0, "alice", "hi"
        )
        ack = build_simp_message(
            MessageType.CONTROL, OperationType.ACK.value, 0, "server", ""
        )
        assert parse_simp_message(msg)["seq"] == parse_simp_message(ack)["seq"]


#############################
#   5. Busy User Error Case
#############################

class TestBusyUser:
    def test_busy_err_fin(self):
        err = build_simp_message(
            MessageType.CONTROL,
            OperationType.ERR.value,
            0,
            "daemon",
            "User is busy in another chat"
        )
        fin = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            0,
            "daemon",
            ""
        )

        p_err = parse_simp_message(err)
        p_fin = parse_simp_message(fin)

        assert p_err["operation"] == OperationType.ERR.value
        assert "busy" in p_err["payload"].lower()
        assert p_fin["operation"] == OperationType.FIN.value


#############################
#   6. Daemon-client protocol
#############################

class TestDaemonClientProtocol:
    def test_client_connect(self):
        msg = build_client_daemon_message("connect", username="alice")
        parsed = parse_client_daemon_message(msg)
        assert parsed["command"] == "connect"
        assert parsed["username"] == "alice"

    def test_client_chat(self):
        msg = build_client_daemon_message("chat", text="hello")
        parsed = parse_client_daemon_message(msg)
        assert parsed["command"] == "chat"
        assert parsed["text"] == "hello"

    def test_client_quit(self):
        msg = build_client_daemon_message("quit")
        parsed = parse_client_daemon_message(msg)
        assert parsed["command"] == "quit"


#########################################
# Run with python test.py
#########################################

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
