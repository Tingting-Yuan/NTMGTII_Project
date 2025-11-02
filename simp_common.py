#!/usr/bin/env python3

import socket
import struct
from enum import Enum
import string

MESSAGE_TYPE_SIZE = 1
OPERATION_SIZE = 1
SEQ_SIZE = 1
USERNAME_SIZE = 32
PAYLOAD_SIZE = 4
MAX_HEADER_SIZE = MESSAGE_TYPE_SIZE + OPERATION_SIZE + SEQ_SIZE + USERNAME_SIZE + PAYLOAD_SIZE

username = 'default'


class MessageType(Enum):
    UNKNOWN = 0
    CHAT = 1,
    CONTROL = 2

    def to_bytes(self):
        if self == MessageType.UNKNOWN:
            return int(0).to_bytes(1, byteorder='big')
        elif self == MessageType.CHAT:
            return int(1).to_bytes(1, byteorder='big')
        elif self == MessageType.CONTROL:
            return int(2).to_bytes(1, byteorder='big')

    @staticmethod
    def to_message_type(type_byte):
        if type_byte == 1:
            return MessageType.CHAT
        elif type_byte == 2:
            return MessageType.CONTROL
        return MessageType.UNKNOWN


class OperationType(Enum):
    NO_OPERATION = 0
    ERROR = 1,
    SYN = 2,
    ACK = 3,
    FIN = 4

    def to_bytes(self):
        if self == OperationType.NO_OPERATION:
            return int(0).to_bytes(1, byteorder='big')
        elif self == OperationType.ERROR:
            return int(1).to_bytes(1, byteorder='big')
        elif self == OperationType.SYN:
            return int(2).to_bytes(1, byteorder='big')
        elif self == OperationType.ACK:
            return int(4).to_bytes(1, byteorder='big')
        elif self == OperationType.FIN:
            return int(8).to_bytes(1, byteorder='big')


class ErrorCode(Enum):
    OK = 0,
    MESSAGE_TOO_SHORT = 1
    UNKNOWN_MESSAGE = 2
    WRONG_PAYLOAD = 3


class HeaderInfo:
    is_ok = False
    type: MessageType
    operation: OperationType
    code: ErrorCode
    seq: int
    user: string

    def __init__(self):
        self.is_ok = False
        self.type = MessageType.UNKNOWN
        self.code = ErrorCode.OK
        self.operation = OperationType.NO_OPERATION
        self.seq = 0
        self.user = ''


class SimpConnectionState:
    address: string
    port: int


def get_message_type(message: bytes) -> MessageType:
    """
    Extracts the message type from the message
    :param message: The received message
    :return: The message type
    """
    type_byte = message[0]
    if type_byte == 1:
        return MessageType.CHAT
    elif type_byte == 2:
        return MessageType.CONTROL
    return MessageType.UNKNOWN


def get_payload_size(message: bytes):
    """
    Returns the declared payload size from the message
    :param message: The received message
    :return: The payload size in bytes
    """
    start_payload_size = MESSAGE_TYPE_SIZE + OPERATION_SIZE + SEQ_SIZE + USERNAME_SIZE
    payload_size = message[start_payload_size:start_payload_size+MAX_HEADER_SIZE]
    return int.from_bytes(payload_size, byteorder='big')


def get_user(message: bytes):
    """
    Returns the username specified in the header
    :param message: The received message
    :return: The username as a string
    """
    start_username = MESSAGE_TYPE_SIZE + OPERATION_SIZE + SEQ_SIZE
    username = message[start_username:start_username+USERNAME_SIZE].decode(encoding='ascii').strip()
    return username


def get_message_payload(message: bytes):
    """
    Returns the payload of the message
    :param message: The received message
    :return: The payload of the message
    """
    start_payload = MESSAGE_TYPE_SIZE + OPERATION_SIZE + SEQ_SIZE + USERNAME_SIZE + PAYLOAD_SIZE
    payload_size = get_payload_size(message)
    payload = message[start_payload:start_payload+payload_size].decode(encoding='ascii').strip()
    return payload


def check_header(message: bytes) -> HeaderInfo:
    """
    Checks if header is correctly built
    :param message: The message to check
    :return: True if header is ok, or False otherwise
    """
    header_info = HeaderInfo()
    if len(message) <= MAX_HEADER_SIZE:
        header_info.code = ErrorCode.MESSAGE_TOO_SHORT
        return header_info

    header_info.code = ErrorCode.OK
    header_info.is_ok = True
    header_info.user = get_user(message)
    header_info.type = MessageType.to_message_type(message[0])

    return header_info


def build_ack(header_info: HeaderInfo, user) -> bytes:
    """
    Builds reply message
    :param header_info: The previously extracted header information
    :return: The reply object as a sequence of bytes
    """
    error_message_str = "OK"
    if header_info.code is ErrorCode.MESSAGE_TOO_SHORT:
        error_message_str = "Message too short"
    elif header_info.code is ErrorCode.WRONG_PAYLOAD:
        error_message_str = "Wrong payload"
    elif header_info.code is ErrorCode.UNKNOWN_MESSAGE:
        error_message_str = "Unknown type of message"

    message_type = MessageType.CONTROL.to_bytes()
    operation_type = OperationType.ACK.to_bytes()
    seq_ack = header_info.seq.to_bytes(1, byteorder='big')
    username_send = user.ljust(USERNAME_SIZE, ' ').encode(encoding='ascii')
    error_message = error_message_str.encode(encoding='ascii')
    payload_size = len(error_message).to_bytes(4, byteorder='big')
    return b''.join([message_type, operation_type, seq_ack, username_send, payload_size, error_message])


def get_username_input():
    username_ok = False
    username_input = ''
    while username_ok is False:
        print('Please enter your user name: ')
        username_input = input()
        if username_input == '':
            print('Error: user name should be a non-empty string')
            continue
        if len(username_input) > 32:
            print('Error: user name should be a string with maximum length of 32 characters')
            continue
        username_ok = True
    return username_input


def handle_message(data, user, host_from, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', port))

    header_info = check_header(data)
    if header_info.type == MessageType.CHAT:
        payload = get_message_payload(data)
        print(f'[{header_info.user}]: {payload}')
        data_send = build_ack(header_info, user)
        print('Sending ACK...')
        s.sendto(data_send, host_from)
        s.close()
        message_to_send = input_message()
        reply = send_message(*host_from, user, message_to_send, port)
    else:
        s.close()


def wait_and_receive(host, port, user):
    print(f'Waiting for connections on port {port}...')
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((host, port))

        data, host_from = s.recvfrom(1024)
        print('Connected by ', host_from)
        if not data:
            continue

        s.close()
        handle_message(data, user, host_from, port)


def send_message(host, port, user, message, local_port) -> string:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('', local_port))
        message_type = MessageType.CHAT.to_bytes()
        operation_type = OperationType.NO_OPERATION.to_bytes()
        seq_ack = int(0).to_bytes(1, byteorder='big')
        username_send = user.ljust(USERNAME_SIZE, ' ').encode(encoding='ascii')
        message_send = message.encode(encoding='ascii')
        payload_size = len(message_send).to_bytes(4, byteorder='big')
        data_send = b''.join([message_type, operation_type, seq_ack, username_send, payload_size, message_send])
        s.sendto(data_send, (host, port))
        print('Message sent. Waiting for reply...')
        reply = s.recvfrom(1024)
        s.close()
        return reply


def input_message():
    print('Please enter message to send: ')
    message_to_send = input()
    return message_to_send
