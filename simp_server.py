#!/usr/bin/env python3

import sys
from simp_common import *


def show_usage():
    print('Usage: simp_server.py <host> <port>')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        show_usage()
        exit(1)

    print('Welcome to SIMP server 1.0.0')
    username = get_username_input()
    wait_and_receive(sys.argv[1], int(sys.argv[2]), username)
