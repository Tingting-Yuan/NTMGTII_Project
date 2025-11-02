#!/usr/bin/env python3

import sys
from simp_common import *


def show_usage():
    print('Usage parameters: simp_client.py <remote_host> <remote_port> <local_port>')


if __name__ == "__main__":
    if len(sys.argv) != 4:
        show_usage()
        exit(1)

    print('Welcome to SIMP client 1.0.0')
    username = get_username_input()
    message_to_send = ''

    while True:
        message_to_send = input_message()
        if message_to_send == 'quit':
            break

        local_port = int(sys.argv[3])
        remote_host = sys.argv[1]
        remote_port = int(sys.argv[2])

        data = send_message(remote_host, remote_port, username, message_to_send, local_port)
        # handle_message(data, username, (remote_host, remote_port), local_port)

        wait_and_receive('', local_port, username)

    print('Bye!')
