#!/usr/bin/env python3

import socket
import struct
from enum import Enum

# Constants
MESSAGE_TYPE_SIZE = 1
OPERATION_SIZE = 1
SEQ_SIZE = 1
USERNAME_SIZE = 32
PAYLOAD_SIZE = 4
HEADER_SIZE = MESSAGE_TYPE_SIZE + OPERATION_SIZE + SEQ_SIZE + USERNAME_SIZE + PAYLOAD_SIZE

DAEMON_PORT = 7777
DAEMON_ADDR = ("127.0.0.1", 7777)
CLIENT_DAEMON_PORT = 7778
TIMEOUT = 2


class MessageType(Enum):
    CONTROL = 0x01
    CHAT = 0x02


class OperationType(Enum):
    ERR = 0x01
    SYN = 0x02
    ACK = 0x04
    FIN = 0x08
    CHAT_MSG = 0x01  # For chat messages


def build_simp_message(msg_type: MessageType, operation: int, seq: int, username: str, payload: str = "") -> bytes:
    """Build a SIMP protocol message."""
    type_byte = msg_type.value.to_bytes(1, byteorder='big')
    op_byte = operation.to_bytes(1, byteorder='big')
    seq_byte = seq.to_bytes(1, byteorder='big')
    
    # Pad username to 32 bytes
    username_bytes = username[:32].ljust(32).encode('ascii')
    
    # Encode payload
    payload_bytes = payload.encode('ascii')
    payload_len = len(payload_bytes).to_bytes(4, byteorder='big')
    
    return type_byte + op_byte + seq_byte + username_bytes + payload_len + payload_bytes



def parse_simp_message(data: bytes) -> dict:
    """Parse a SIMP protocol message."""
    if len(data) < HEADER_SIZE:
        raise ValueError("Message too short")
    
    msg_type = data[0]
    operation = data[1]
    seq = data[2]
    username = data[3:35].decode('ascii').strip()
    payload_len = int.from_bytes(data[35:39], byteorder='big')
    
    if len(data) < HEADER_SIZE + payload_len:
        raise ValueError("Incomplete payload")
    
    payload = data[39:39+payload_len].decode('ascii')
    
    return {
        'type': msg_type,
        'operation': operation,
        'seq': seq,
        'username': username,
        'length': payload_len,
        'payload': payload
    }


def build_client_daemon_message(cmd: str, **kwargs) -> str:
    """Build internal client-daemon protocol message."""
    parts = [cmd]
    for key, value in kwargs.items():
        parts.append(f"{key}={value}")
    return "|".join(parts)


def parse_client_daemon_message(msg: str) -> dict:
    """Parse internal client-daemon protocol message."""
    parts = msg.split("|")
    result = {'command': parts[0]}
    for part in parts[1:]:
        if '=' in part:
            key, value = part.split('=', 1)
            result[key] = value
    return result
