#!/usr/bin/env python3

import socket
import sys
import threading
import time
from simp_common import *


class SimpDaemon:
    def __init__(self, host='0.0.0.0'):
        self.host = host
        self.username = None
        self.in_chat = False
        self.chat_partner = None
        self.chat_partner_username = None
        self.seq_num = 0
        self.expected_seq = 0
        self.pending_invitation = None
        self.client_socket = None
        self.daemon_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.daemon_socket.bind((self.host, DAEMON_PORT))
        self.client_daemon_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_daemon_socket.bind((self.host, CLIENT_DAEMON_PORT))
        # self.client_daemon_socket2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.client_daemon_socket2.bind((self.host, Test_PORT))
        self.running = True

    def start(self):
        """Start the daemon with both listeners."""
        print(f"SIMP Daemon started on {self.host}")
        print(f"Listening for SIMP on port {DAEMON_PORT}")
        print(f"Listening for clients on port {CLIENT_DAEMON_PORT}")
        
        # Start daemon-to-daemon listener
        daemon_thread = threading.Thread(target=self.listen_daemon, daemon=True)
        daemon_thread.start()
        
        # Start client-daemon listener in main thread
        self.listen_client()

    def listen_daemon(self):
        """Listen for incoming SIMP messages from other daemons."""
        while self.running:
            try:
                data, addr = self.daemon_socket.recvfrom(4096)
                threading.Thread(target=self.handle_daemon_message, args=(data, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error in daemon listener: {e}")

    def listen_client(self):
        """Listen for messages from local client."""
        while self.running:
            try:
                data, addr = self.client_daemon_socket.recvfrom(4096)
                self.client_socket = addr
                self.handle_client_message(data.decode('ascii'), addr)
            except Exception as e:
                if self.running:
                    print(f"Error in client listener: {e}")

    def handle_daemon_message(self, data: bytes, addr: tuple):
        """Handle incoming SIMP protocol messages."""
        try:
            msg = parse_simp_message(data)
            
            if msg['type'] == MessageType.CONTROL.value:
                if msg['operation'] == OperationType.SYN.value:
                    self.handle_syn(msg, addr)
                elif msg['operation'] == (OperationType.SYN.value | OperationType.ACK.value):
                    self.handle_syn_ack(msg, addr)
                elif msg['operation'] == OperationType.ACK.value:
                    self.handle_ack(msg, addr)
                elif msg['operation'] == OperationType.FIN.value:
                    self.handle_fin(msg, addr)
                elif msg['operation'] == OperationType.ERR.value:
                    self.handle_error(msg, addr)
                    
            elif msg['type'] == MessageType.CHAT.value:
                self.handle_chat_message(msg, addr)
                
        except Exception as e:
            print(f"Error handling daemon message: {e}")

    def handle_syn(self, msg: dict, addr: tuple):
        """Handle SYN (connection request)."""
        if self.in_chat:
            # Already in chat, send error
            error_msg = build_simp_message(
                MessageType.CONTROL,
                OperationType.ERR.value,
                0,
                self.username or "unknown",
                "User already in another chat"
            )
            self.daemon_socket.sendto(error_msg, addr)
            fin_msg = build_simp_message(
                MessageType.CONTROL,
                OperationType.FIN.value,
                0,
                self.username or "unknown"
            )
            self.daemon_socket.sendto(fin_msg, addr)
        else:
            # Store invitation for client to accept/decline
            self.pending_invitation = {
                'addr': addr,
                'username': msg['username'],
                'seq': msg['seq']
            }
            # Notify client
            if self.client_socket:
                notification = build_client_daemon_message(
                    'invitation',
                    username=msg['username'],
                    ip=addr[0]
                )
                self.client_daemon_socket.sendto(notification.encode('ascii'), self.client_socket)

    def handle_syn_ack(self, msg: dict, addr: tuple):
        """Handle SYN-ACK (connection accepted)."""
        # Send final ACK to complete handshake
        ack_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            msg['seq'],
            self.username
        )
        self.daemon_socket.sendto(ack_msg, addr)
        
        # Connection established
        self.in_chat = True
        self.chat_partner = addr
        self.chat_partner_username = msg['username']
        self.seq_num = 0
        self.expected_seq = 0
        
        # Notify client
        if self.client_socket:
            notification = build_client_daemon_message('connected', username=msg['username'])
            self.client_daemon_socket.sendto(notification.encode('ascii'), self.client_socket)

    def handle_ack(self, msg: dict, addr: tuple):
        """Handle ACK."""
        if not self.in_chat and self.pending_invitation:
            # This is the final ACK of handshake (we sent SYN-ACK)
            self.in_chat = True
            self.chat_partner = addr
            self.chat_partner_username = msg['username']
            self.seq_num = 0
            self.expected_seq = 0
            self.pending_invitation = None
            
            # Notify client
            if self.client_socket:
                notification = build_client_daemon_message('connected', username=msg['username'])
                self.client_daemon_socket.sendto(notification.encode('ascii'), self.client_socket)
        else:
            # ACK for a chat message - toggle sequence number
            if msg['seq'] == self.seq_num:
                self.seq_num = 1 - self.seq_num

    def handle_fin(self, msg: dict, addr: tuple):
        """Handle FIN (connection termination)."""
        # Send ACK
        ack_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.ACK.value,
            msg['seq'],
            self.username or "unknown"
        )
        self.daemon_socket.sendto(ack_msg, addr)
        
        # Clear chat state
        self.in_chat = False
        self.chat_partner = None
        self.chat_partner_username = None
        self.seq_num = 0
        self.expected_seq = 0
        
        # Notify client
        if self.client_socket:
            notification = build_client_daemon_message('disconnected')
            self.client_daemon_socket.sendto(notification.encode('ascii'), self.client_socket)

    def handle_error(self, msg: dict, addr: tuple):
        """Handle ERR message."""
        print(f"Error from {addr}: {msg['payload']}")
        if self.client_socket:
            notification = build_client_daemon_message('error', message=msg['payload'])
            self.client_daemon_socket.sendto(notification.encode('ascii'), self.client_socket)

    def handle_chat_message(self, msg: dict, addr: tuple):
        """Handle incoming chat message."""
        if not self.in_chat or addr != self.chat_partner:
            return
        
        # Check sequence number
        if msg['seq'] == self.expected_seq:
            # Send ACK
            ack_msg = build_simp_message(
                MessageType.CONTROL,
                OperationType.ACK.value,
                msg['seq'],
                self.username
            )
            self.daemon_socket.sendto(ack_msg, addr)
            
            # Toggle expected sequence
            self.expected_seq = 1 - self.expected_seq
            
            # Forward to client
            if self.client_socket:
                notification = build_client_daemon_message(
                    'message',
                    username=msg['username'],
                    text=msg['payload']
                )
                self.client_daemon_socket.sendto(notification.encode('ascii'), self.client_socket)

    def handle_client_message(self, msg: str, addr: tuple):
        """Handle messages from local client."""
        try:
            parsed = parse_client_daemon_message(msg)
            cmd = parsed['command']
            
            if cmd == 'connect':
                self.username = parsed.get('username', 'anonymous')
                response = build_client_daemon_message('ok')
                self.client_daemon_socket.sendto(response.encode('ascii'), addr)
                
            elif cmd == 'invite':
                target_ip = parsed['ip']
                target_port = int(parsed.get('port', DAEMON_PORT))
                self.initiate_chat(target_ip, target_port)
                
            elif cmd == 'accept':
                self.accept_invitation()
                
            elif cmd == 'decline':
                self.decline_invitation()
                
            elif cmd == 'send':
                text = parsed['text']
                self.send_chat_message(text)
                
            elif cmd == 'quit':
                self.terminate_chat()
                response = build_client_daemon_message('ok')
                self.client_daemon_socket.sendto(response.encode('ascii'), addr)
                
        except Exception as e:
            print(f"Error handling client message: {e}")

    def initiate_chat(self, target_ip: str, target_port: int):
        """Initiate a chat connection (send SYN)."""
        syn_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value,
            0,
            self.username
        )
        self.daemon_socket.sendto(syn_msg, (target_ip, target_port))

    def accept_invitation(self):
        """Accept a pending invitation."""
        if not self.pending_invitation:
            return
        
        inv = self.pending_invitation
        syn_ack_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.SYN.value | OperationType.ACK.value,
            inv['seq'],
            self.username
        )
        self.daemon_socket.sendto(syn_ack_msg, inv['addr'])

    def decline_invitation(self):
        """Decline a pending invitation."""
        if not self.pending_invitation:
            return
        
        inv = self.pending_invitation
        fin_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            inv['seq'],
            self.username
        )
        self.daemon_socket.sendto(fin_msg, inv['addr'])
        self.pending_invitation = None

    def send_chat_message(self, text: str):
        """Send a chat message with stop-and-wait."""
        if not self.in_chat:
            return
        
        chat_msg = build_simp_message(
            MessageType.CHAT,
            OperationType.CHAT_MSG.value,
            self.seq_num,
            self.username,
            text
        )
        
        # Stop-and-wait: retry until ACK received
        max_retries = 5
        for attempt in range(max_retries):
            self.daemon_socket.sendto(chat_msg, self.chat_partner)
            
            # Wait for ACK with timeout
            self.daemon_socket.settimeout(TIMEOUT)
            try:
                # ACK will be handled by handle_ack which toggles seq_num
                # Just wait a bit for the ACK handler to process
                time.sleep(0.1)
                break
            except socket.timeout:
                print(f"Timeout, retrying... (attempt {attempt + 1})")
        
        self.daemon_socket.settimeout(None)

    def terminate_chat(self):
        """Terminate current chat."""
        if not self.in_chat:
            return
        
        fin_msg = build_simp_message(
            MessageType.CONTROL,
            OperationType.FIN.value,
            0,
            self.username
        )
        self.daemon_socket.sendto(fin_msg, self.chat_partner)
        
        self.in_chat = False
        self.chat_partner = None
        self.chat_partner_username = None

    def stop(self):
        """Stop the daemon."""
        self.running = False
        self.daemon_socket.close()
        self.client_daemon_socket.close()


def main():
    if len(sys.argv) < 1:
        print("Usage: simp_daemon.py")
        sys.exit(1)
    
    daemon = SimpDaemon()
    try:
        daemon.start()
    except KeyboardInterrupt:
        print("\nShutting down daemon...")
        daemon.stop()


if __name__ == "__main__":
    main()
