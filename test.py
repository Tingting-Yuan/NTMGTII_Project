import pytest
import socket
import threading
import time
from simp_common import *
from simp_daemon import SimpDaemon


class TestSimpCommon:
    """Test suite for simp_common.py functions"""
    
    def test_build_control_syn_message(self):
        """Test building SYN control message"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "alice",
            ""
        )
        assert len(msg) >= HEADER_SIZE
        assert msg[0] == MessageType.CONTROL.value
        assert msg[1] == OperationType.SYN.value
        assert msg[2] == 0  # sequence number
    
    def test_build_control_ack_message(self):
        """Test building ACK control message"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            1,
            "bob",
            ""
        )
        assert msg[0] == MessageType.CONTROL.value
        assert msg[1] == OperationType.ACK.value
        assert msg[2] == 1
    
    def test_build_control_fin_message(self):
        """Test building FIN control message"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            0,
            "charlie",
            ""
        )
        assert msg[0] == MessageType.CONTROL.value
        assert msg[1] == OperationType.FIN.value
    
    def test_build_control_error_message(self):
        """Test building ERROR control message with payload"""
        error_text = "User already in another chat"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ERR.value,
            0,
            "alice",
            error_text
        )
        assert msg[0] == MessageType.CONTROL.value
        assert msg[1] == OperationType.ERR.value
        assert len(msg) == HEADER_SIZE + len(error_text)
    
    def test_build_chat_message(self):
        """Test building chat message with payload"""
        payload = "Hello, World!"
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            1,
            "alice",
            payload
        )
        assert len(msg) == HEADER_SIZE + len(payload)
        assert msg[0] == MessageType.CHAT.value
        assert msg[1] == OperationType.CHAT_MSG.value
    
    def test_build_syn_ack_message(self):
        """Test building SYN-ACK message (bitwise OR)"""
        syn_ack_value = OperationType.SYN.value | OperationType.ACK.value
        msg = build_simp_message(
            MessageType.CONTROL,
            syn_ack_value,
            0,
            "bob",
            ""
        )
        assert msg[1] == 0x06  # 0x02 | 0x04
    
    def test_parse_control_message(self):
        """Test parsing control message"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "alice",
            ""
        )
        
        parsed = parse_simp_message(msg)
        assert parsed['type'] == MessageType.CONTROL.value
        assert parsed['operation'] == OperationType.SYN.value
        assert parsed['seq'] == 0
        assert parsed['username'] == "alice"
        assert parsed['payload'] == ""
    
    def test_parse_chat_message(self):
        """Test parsing chat message with payload"""
        original_payload = "Test message content"
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            1,
            "bob",
            original_payload
        )
        
        parsed = parse_simp_message(msg)
        assert parsed['type'] == MessageType.CHAT.value
        assert parsed['operation'] == OperationType.CHAT_MSG.value
        assert parsed['seq'] == 1
        assert parsed['username'] == "bob"
        assert parsed['payload'] == original_payload
    
    def test_username_padding_short(self):
        """Test username padding for short names"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "joe",
            ""
        )
        # Username field should always be 32 bytes
        username_bytes = msg[3:35]
        assert len(username_bytes) == 32
        
        parsed = parse_simp_message(msg)
        assert parsed['username'] == "joe"
    
    def test_username_padding_exact_32(self):
        """Test username exactly 32 characters"""
        username_32 = "a" * 32
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            username_32,
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed['username'] == username_32
    
    def test_username_truncation_over_32(self):
        """Test long username is truncated to 32 chars"""
        long_name = "a" * 50
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            long_name,
            ""
        )
        parsed = parse_simp_message(msg)
        assert len(parsed['username']) == 32
        assert parsed['username'] == "a" * 32
    
    def test_sequence_number_0(self):
        """Test sequence number 0"""
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            "message"
        )
        parsed = parse_simp_message(msg)
        assert parsed['seq'] == 0
    
    def test_sequence_number_1(self):
        """Test sequence number 1"""
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            1,
            "user",
            "message"
        )
        parsed = parse_simp_message(msg)
        assert parsed['seq'] == 1
    
    def test_empty_payload(self):
        """Test message with empty payload"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            1,
            "user",
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == ""
        assert len(msg) == HEADER_SIZE
    
    def test_large_payload(self):
        """Test message with large payload"""
        large_payload = "A" * 1000
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            large_payload
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == large_payload
        assert len(parsed['payload']) == 1000
    
    def test_payload_with_spaces(self):
        """Test payload with spaces"""
        payload = "Hello World Test Message"
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            payload
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == payload
    
    def test_payload_with_special_chars(self):
        """Test payload with special ASCII characters"""
        payload = "Hello! @#$%^&*() 123"
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            payload
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == payload
    
    def test_message_too_short_error(self):
        """Test parsing fails for message shorter than header"""
        short_msg = b'tooshort'
        with pytest.raises(ValueError, match="Message too short"):
            parse_simp_message(short_msg)
    
    def test_incomplete_payload_error(self):
        """Test parsing fails when payload is incomplete"""
        # Build a valid header but truncate the payload
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            "This is a long message"
        )
        # Truncate to only partial payload
        truncated = msg[:HEADER_SIZE + 5]
        with pytest.raises(ValueError, match="Incomplete payload"):
            parse_simp_message(truncated)
    
    def test_build_client_daemon_connect(self):
        """Test building client-daemon connect message"""
        msg = build_client_daemon_message('connect', username='alice')
        assert 'connect' in msg
        assert 'username=alice' in msg
    
    def test_build_client_daemon_invite(self):
        """Test building client-daemon invite message"""
        msg = build_client_daemon_message('invite', ip='192.168.1.1', port='7777')
        assert 'invite' in msg
        assert 'ip=192.168.1.1' in msg
        assert 'port=7777' in msg
    
    def test_build_client_daemon_send(self):
        """Test building client-daemon send message"""
        msg = build_client_daemon_message('send', text='Hello World')
        assert 'send' in msg
        assert 'text=Hello World' in msg
    
    def test_parse_client_daemon_connect(self):
        """Test parsing client-daemon connect message"""
        msg = build_client_daemon_message('connect', username='bob')
        parsed = parse_client_daemon_message(msg)
        assert parsed['command'] == 'connect'
        assert parsed['username'] == 'bob'
    
    def test_parse_client_daemon_with_multiple_params(self):
        """Test parsing client-daemon message with multiple parameters"""
        msg = build_client_daemon_message('invite', ip='10.0.0.1', port='7777')
        parsed = parse_client_daemon_message(msg)
        assert parsed['command'] == 'invite'
        assert parsed['ip'] == '10.0.0.1'
        assert parsed['port'] == '7777'
    
    def test_parse_client_daemon_no_params(self):
        """Test parsing client-daemon message with no parameters"""
        msg = build_client_daemon_message('quit')
        parsed = parse_client_daemon_message(msg)
        assert parsed['command'] == 'quit'
    
    def test_header_size_constant(self):
        """Test header size constant is correct"""
        assert HEADER_SIZE == 39  # 1 + 1 + 1 + 32 + 4
    
    def test_daemon_port_constant(self):
        """Test daemon port constant"""
        assert DAEMON_PORT == 7777
    
    def test_client_daemon_port_constant(self):
        """Test client-daemon port constant"""
        assert CLIENT_DAEMON_PORT == 7778
    
    def test_timeout_constant(self):
        """Test timeout constant"""
        assert TIMEOUT == 5.0


class TestProtocolOperations:
    """Test SIMP protocol operations"""
    
    def test_three_way_handshake_step1_syn(self):
        """Test step 1 of handshake: SYN"""
        syn_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "alice",
            ""
        )
        parsed = parse_simp_message(syn_msg)
        assert parsed['type'] == MessageType.CONTROL.value
        assert parsed['operation'] == OperationType.SYN.value
        assert parsed['seq'] == 0
    
    def test_three_way_handshake_step2_syn_ack(self):
        """Test step 2 of handshake: SYN-ACK"""
        syn_ack_value = OperationType.SYN.value | OperationType.ACK.value
        syn_ack_msg = build_simp_message(
            MessageType.CONTROL,
            syn_ack_value,
            0,
            "bob",
            ""
        )
        parsed = parse_simp_message(syn_ack_msg)
        assert parsed['type'] == MessageType.CONTROL.value
        assert parsed['operation'] == 0x06  # 0x02 | 0x04
    
    def test_three_way_handshake_step3_ack(self):
        """Test step 3 of handshake: ACK"""
        ack_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            0,
            "alice",
            ""
        )
        parsed = parse_simp_message(ack_msg)
        assert parsed['type'] == MessageType.CONTROL.value
        assert parsed['operation'] == OperationType.ACK.value
    
    def test_handshake_rejection_fin(self):
        """Test handshake rejection with FIN"""
        fin_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            0,
            "bob",
            ""
        )
        parsed = parse_simp_message(fin_msg)
        assert parsed['operation'] == OperationType.FIN.value
    
    def test_stop_and_wait_sequence_toggle(self):
        """Test sequence number toggling in stop-and-wait"""
        seq = 0
        for i in range(10):
            expected = i % 2
            assert seq == expected
            seq = 1 - seq  # Toggle: 0->1, 1->0
    
    def test_stop_and_wait_message_ack_pair_seq0(self):
        """Test message-ACK pair with sequence 0"""
        # Message
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "alice",
            "Hello"
        )
        parsed_msg = parse_simp_message(msg)
        
        # ACK
        ack = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            0,
            "bob",
            ""
        )
        parsed_ack = parse_simp_message(ack)
        
        assert parsed_msg['seq'] == parsed_ack['seq']
        assert parsed_msg['seq'] == 0
    
    def test_stop_and_wait_message_ack_pair_seq1(self):
        """Test message-ACK pair with sequence 1"""
        # Message
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            1,
            "alice",
            "World"
        )
        parsed_msg = parse_simp_message(msg)
        
        # ACK
        ack = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            1,
            "bob",
            ""
        )
        parsed_ack = parse_simp_message(ack)
        
        assert parsed_msg['seq'] == parsed_ack['seq']
        assert parsed_msg['seq'] == 1
    
    def test_error_message_user_busy(self):
        """Test error message for busy user"""
        error_text = "User already in another chat"
        err_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ERR.value,
            0,
            "alice",
            error_text
        )
        parsed = parse_simp_message(err_msg)
        assert parsed['operation'] == OperationType.ERR.value
        assert parsed['payload'] == error_text
    
    def test_connection_termination_fin_ack(self):
        """Test connection termination with FIN-ACK"""
        # FIN
        fin_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            0,
            "alice",
            ""
        )
        parsed_fin = parse_simp_message(fin_msg)
        
        # ACK response
        ack_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            0,
            "bob",
            ""
        )
        parsed_ack = parse_simp_message(ack_msg)
        
        assert parsed_fin['operation'] == OperationType.FIN.value
        assert parsed_ack['operation'] == OperationType.ACK.value


class TestDaemonInitialization:
    """Test daemon initialization and state"""
    
    def test_daemon_init_default_host(self):
        """Test daemon initializes with default host"""
        daemon = SimpDaemon()
        assert daemon.host == '0.0.0.0'
        assert daemon.username is None
        assert daemon.in_chat == False
        assert daemon.chat_partner is None
        assert daemon.seq_num == 0
        assert daemon.expected_seq == 0
        daemon.stop()
    
    def test_daemon_init_custom_host(self):
        """Test daemon initializes with custom host"""
        daemon = SimpDaemon('127.0.0.1')
        assert daemon.host == '127.0.0.1'
        daemon.stop()
    
    def test_daemon_initial_state(self):
        """Test daemon initial state values"""
        daemon = SimpDaemon()
        assert daemon.in_chat == False
        assert daemon.chat_partner is None
        assert daemon.chat_partner_username is None
        assert daemon.pending_invitation is None
        assert daemon.running == True
        daemon.stop()
    
    def test_daemon_sequence_numbers_initial(self):
        """Test daemon sequence numbers are initially 0"""
        daemon = SimpDaemon()
        assert daemon.seq_num == 0
        assert daemon.expected_seq == 0
        daemon.stop()


class TestMessageTypeEnum:
    """Test MessageType enum"""
    
    def test_control_message_type_value(self):
        """Test CONTROL message type value"""
        assert MessageType.CONTROL.value == 0x01
    
    def test_chat_message_type_value(self):
        """Test CHAT message type value"""
        assert MessageType.CHAT.value == 0x02


class TestOperationTypeEnum:
    """Test OperationType enum"""
    
    def test_err_operation_value(self):
        """Test ERR operation value"""
        assert OperationType.ERR.value == 0x01
    
    def test_syn_operation_value(self):
        """Test SYN operation value"""
        assert OperationType.SYN.value == 0x02
    
    def test_ack_operation_value(self):
        """Test ACK operation value"""
        assert OperationType.ACK.value == 0x04
    
    def test_fin_operation_value(self):
        """Test FIN operation value"""
        assert OperationType.FIN.value == 0x08
    
    def test_syn_ack_bitwise_or(self):
        """Test SYN-ACK bitwise OR operation"""
        syn_ack = OperationType.SYN.value | OperationType.ACK.value
        assert syn_ack == 0x06


class TestEdgeCasesAndErrors:
    """Test edge cases and error conditions"""
    
    def test_empty_username(self):
        """Test message with empty username"""
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            "",
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed['username'] == ""
    
    def test_username_with_numbers(self):
        """Test username with numbers"""
        username = "user123"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            username,
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed['username'] == username
    
    def test_username_with_underscores(self):
        """Test username with underscores"""
        username = "user_name_123"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            username,
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed['username'] == username
    
    def test_username_with_hyphens(self):
        """Test username with hyphens"""
        username = "user-name-123"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            username,
            ""
        )
        parsed = parse_simp_message(msg)
        assert parsed['username'] == username
    
    def test_payload_single_character(self):
        """Test payload with single character"""
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            "A"
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == "A"
    
    def test_payload_with_numbers(self):
        """Test payload with numbers"""
        payload = "Test message 123 456"
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            payload
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == payload
    
    def test_payload_with_punctuation(self):
        """Test payload with punctuation"""
        payload = "Hello! How are you? I'm fine."
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            payload
        )
        parsed = parse_simp_message(msg)
        assert parsed['payload'] == payload
    
    def test_max_size_message(self):
        """Test message with maximum reasonable size"""
        large_payload = "X" * 4096
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            0,
            "user",
            large_payload
        )
        parsed = parse_simp_message(msg)
        assert len(parsed['payload']) == 4096
    
    def test_client_daemon_message_with_equals_in_value(self):
        """Test client-daemon message with = in value"""
        msg = build_client_daemon_message('send', text='2+2=4')
        parsed = parse_client_daemon_message(msg)
        assert parsed['text'] == '2+2=4'
    
    def test_client_daemon_message_with_pipe_safe(self):
        """Test client-daemon message parsing is safe"""
        msg = "command|param1=value1|param2=value2"
        parsed = parse_client_daemon_message(msg)
        assert parsed['command'] == 'command'
        assert parsed['param1'] == 'value1'
        assert parsed['param2'] == 'value2'


class TestRoundTripMessages:
    """Test building and parsing messages (round trip)"""
    
    def test_roundtrip_control_syn(self):
        """Test SYN message round trip"""
        original_username = "alice"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            original_username,
            ""
        )
        parsed = parse_simp_message(msg)
        
        assert parsed['type'] == MessageType.CONTROL.value
        assert parsed['operation'] == OperationType.SYN.value
        assert parsed['username'] == original_username
    
    def test_roundtrip_chat_message(self):
        """Test chat message round trip"""
        original_username = "bob"
        original_payload = "This is a test message!"
        
        msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            1,
            original_username,
            original_payload
        )
        parsed = parse_simp_message(msg)
        
        assert parsed['username'] == original_username
        assert parsed['payload'] == original_payload
        assert parsed['seq'] == 1
    
    def test_roundtrip_error_message(self):
        """Test error message round trip"""
        error_text = "Connection refused"
        msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ERR.value,
            0,
            "server",
            error_text
        )
        parsed = parse_simp_message(msg)
        
        assert parsed['operation'] == OperationType.ERR.value
        assert parsed['payload'] == error_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
