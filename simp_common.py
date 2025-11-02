#!/usr/bin/env python3

import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional

# Protocol Constants
DAEMON_PORT = 7777
CLIENT_PORT = 7778
TIMEOUT = 5.0
MAX_USERNAME_LEN = 32
HEADER_SIZE = 38  # 1 + 1 + 1 + 32 + 4 + (payload variable)

class DatagramType(IntEnum):
    CONTROL = 0x01
    CHAT = 0x02

class ControlOp(IntEnum):
    ERR = 0x01
    SYN = 0x02
    ACK = 0x04
    FIN = 0x08
    SYN_ACK = 0x06  # SYN | ACK

class ChatOp(IntEnum):
    MESSAGE = 0x01

@dataclass
class SIMPHeader:
    """SIMP Protocol Header"""
    type: int
    operation: int
    sequence: int
    user: str
    length: int
    
    def pack(self) -> bytes:
        """Pack header into bytes"""
        # Pad username to 32 bytes
        user_bytes = self.user.encode('ascii')[:MAX_USERNAME_LEN]
        user_padded = user_bytes.ljust(MAX_USERNAME_LEN, b'\x00')
        
        return struct.pack('!BBB32sI', 
                          self.type, 
                          self.operation, 
                          self.sequence,
                          user_padded,
                          self.length)
    
    @staticmethod
    def unpack(data: bytes) -> 'SIMPHeader':
        """Unpack header from bytes"""
        type_val, op, seq, user_bytes, length = struct.unpack('!BBB32sI', data[:HEADER_SIZE])
        # Remove null padding from username
        user = user_bytes.rstrip(b'\x00').decode('ascii')
        return SIMPHeader(type_val, op, seq, user, length)

@dataclass
class SIMPDatagram:
    """Complete SIMP Datagram"""
    header: SIMPHeader
    payload: bytes
    
    def pack(self) -> bytes:
        """Pack entire datagram"""
        return self.header.pack() + self.payload
    
    @staticmethod
    def unpack(data: bytes) -> 'SIMPDatagram':
        """Unpack entire datagram"""
        header = SIMPHeader.unpack(data[:HEADER_SIZE])
        payload = data[HEADER_SIZE:HEADER_SIZE + header.length]
        return SIMPDatagram(header, payload)
    
    @staticmethod
    def create_control(operation: int, sequence: int, username: str, payload: str = "") -> 'SIMPDatagram':
        """Create a control datagram"""
        payload_bytes = payload.encode('ascii')
        header = SIMPHeader(
            type=DatagramType.CONTROL,
            operation=operation,
            sequence=sequence,
            user=username,
            length=len(payload_bytes)
        )
        return SIMPDatagram(header, payload_bytes)
    
    @staticmethod
    def create_chat(sequence: int, username: str, message: str) -> 'SIMPDatagram':
        """Create a chat datagram"""
        payload_bytes = message.encode('ascii')
        header = SIMPHeader(
            type=DatagramType.CHAT,
            operation=ChatOp.MESSAGE,
            sequence=sequence,
            user=username,
            length=len(payload_bytes)
        )
        return SIMPDatagram(header, payload_bytes)
    
    def get_payload_str(self) -> str:
        """Get payload as string"""
        return self.payload.decode('ascii')

# Internal Client-Daemon Protocol
class ClientCommand(IntEnum):
    CONNECT = 0x01
    CHAT = 0x02
    QUIT = 0x03
    ACCEPT = 0x04
    DECLINE = 0x05
    START_CHAT = 0x06
    WAIT = 0x07

class DaemonResponse(IntEnum):
    OK = 0x01
    ERROR = 0x02
    INVITATION = 0x03
    MESSAGE = 0x04
    CHAT_ENDED = 0x05
    CHAT_ESTABLISHED = 0x06

@dataclass
class ClientDaemonMessage:
    """Message between client and daemon"""
    command: int
    data: str = ""
    
    def pack(self) -> bytes:
        """Pack into bytes"""
        data_bytes = self.data.encode('ascii')
        return struct.pack('!BI', self.command, len(data_bytes)) + data_bytes
    
    @staticmethod
    def unpack(data: bytes) -> 'ClientDaemonMessage':
        """Unpack from bytes"""
        command, length = struct.unpack('!BI', data[:5])
        payload = data[5:5+length].decode('ascii')
        return ClientDaemonMessage(command, payload)


def input_message():
    print('Please enter message to send: ')
    message_to_send = input()
    return message_to_send
