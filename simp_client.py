#!/usr/bin/env python3

import socket
import sys
import threading
from simp_common import *



class SimpClient:
    def __init__(self, daemon_ip='127.0.0.1'):
        self.daemon_ip = daemon_ip
        self.username = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', 0))  # Bind to any available port
        self.in_chat = False
        self.pending_invitation = None
        self.running = True
        
    def start(self):
        """Start the client."""
        print("Welcome to SIMP Client 1.0.0")
        print("=" * 50)
        
        # Get username
        self.username = self.get_username()
        
        # Connect to daemon
        if not self.connect_to_daemon():
            print("Failed to connect to daemon")
            return
        
        # Start listener thread for daemon messages
        listener_thread = threading.Thread(target=self.listen_daemon, daemon=True)
        listener_thread.start()
        
        # Main interaction loop
        self.main_loop()
    
    def get_username(self) -> str:
        """Get username from user."""
        while True:
            username = input("Please enter your username: ").strip()
            if username and len(username) <= 32:
                return username
            print("Username must be non-empty and max 32 characters")
    
    def connect_to_daemon(self) -> bool:
        """Connect to the local daemon."""
        try:
            msg = build_client_daemon_message('connect', username=self.username)
            self.socket.sendto(msg.encode('ascii'), (self.daemon_ip, CLIENT_DAEMON_PORT))
            
            # Wait for response
            self.socket.settimeout(2.0)
            data, _ = self.socket.recvfrom(4096)
            response = parse_client_daemon_message(data.decode('ascii'))
            self.socket.settimeout(None)
            
            if response['command'] == 'ok':
                print(f"Connected to daemon as '{self.username}'")
                return True
            return False
        except Exception as e:
            print(f"Error connecting to daemon: {e}")
            return False
    
    def listen_daemon(self):
        """Listen for messages from daemon."""
        while self.running:
            try:
                data, _ = self.socket.recvfrom(4096)
                msg = parse_client_daemon_message(data.decode('ascii'))
                self.handle_daemon_notification(msg)
            except Exception as e:
                if self.running:
                    print(f"\nError in listener: {e}")
    
    def handle_daemon_notification(self, msg: dict):
        """Handle notifications from daemon."""
        cmd = msg['command']
        
        if cmd == 'invitation':
            self.pending_invitation = {
                'username': msg['username'],
                'ip': msg['ip']
            }
            print(f"\n{'='*50}")
            print(f"📨 Incoming chat invitation!")
            print(f"From: {msg['username']} ({msg['ip']})")
            print(f"{'='*50}")
            
        elif cmd == 'connected':
            self.in_chat = True
            self.pending_invitation = None
            print(f"\n✓ Chat established with {msg['username']}")
            print("Type your messages (or 'q' to quit chat)\n")
            
        elif cmd == 'disconnected':
            self.in_chat = False
            print("\n✗ Chat ended")
            
        elif cmd == 'message':
            print(f"\n[{msg['username']}]: {msg['text']}")
            if self.in_chat:
                print("You: ", end='', flush=True)
                
        elif cmd == 'error':
            print(f"\n⚠ Error: {msg['message']}")
    
    def main_loop(self):
        """Main interaction loop."""
        while self.running:
            try:
                if self.pending_invitation:
                    self.handle_invitation()
                elif self.in_chat:
                    self.chat_mode()
                else:
                    self.idle_mode()
            except KeyboardInterrupt:
                print("\n\nExiting...")
                self.quit()
                break
    
    def handle_invitation(self):
        """Handle pending invitation."""
        inv = self.pending_invitation
        
        while True:
            choice = input("Accept invitation? (y/n): ").strip().lower()
            if choice == 'y':
                msg = build_client_daemon_message('accept')
                self.socket.sendto(msg.encode('ascii'), (self.daemon_ip, CLIENT_DAEMON_PORT))
                print("Accepting invitation...")
                break
            elif choice == 'n':
                msg = build_client_daemon_message('decline')
                self.socket.sendto(msg.encode('ascii'), (self.daemon_ip, CLIENT_DAEMON_PORT))
                self.pending_invitation = None
                print("Invitation declined")
                break
            else:
                print("Please enter 'y' or 'n'")
    
    def chat_mode(self):
        """Active chat mode."""
        try:
            message = input("You: ").strip()
            
            if message.lower() == 'q':
                self.end_chat()
            elif message:
                msg = build_client_daemon_message('send', text=message)
                self.socket.sendto(msg.encode('ascii'), (self.daemon_ip, CLIENT_DAEMON_PORT))
        except EOFError:
            self.end_chat()
    
    def idle_mode(self):
        """Idle mode - waiting for action."""
        print("\n" + "="*50)
        print("Options:")
        print("  1. Start a new chat")
        print("  2. Wait for incoming chat requests")
        print("  q. Quit")
        print("="*50)
        
        choice = input("Your choice: ").strip()
        
        if choice == '1':
            self.start_new_chat()
        elif choice == '2':
            print("Waiting for incoming requests...")
            print("(You can press Ctrl+C to return to menu)")
            try:
                while not self.pending_invitation and not self.in_chat:
                    import time
                    time.sleep(0.5)
            except KeyboardInterrupt:
                print("\nReturning to menu...")
        elif choice.lower() == 'q':
            self.quit()
    
    def start_new_chat(self):
        """Initiate a new chat."""
        target_ip = input("Enter remote user's IP address: ").strip()
        
        if not target_ip:
            print("Invalid IP address")
            return
        
        print(f"Connecting to {target_ip}...")
        msg = build_client_daemon_message('invite', ip=target_ip, port=str(DAEMON_PORT))
        self.socket.sendto(msg.encode('ascii'), (self.daemon_ip, CLIENT_DAEMON_PORT))
        print("Invitation sent. Waiting for response...")
    
    def end_chat(self):
        """End current chat."""
        msg = build_client_daemon_message('quit')
        self.socket.sendto(msg.encode('ascii'), (self.daemon_ip, CLIENT_DAEMON_PORT))
        self.in_chat = False
        print("Chat ended")
    
    def quit(self):
        """Quit the client."""
        if self.in_chat:
            self.end_chat()
        self.running = False
        self.socket.close()
        print("Goodbye!")
        sys.exit(0)


def main():
    if len(sys.argv) < 2:
        daemon_ip = '127.0.0.1'
        print(f"Using default daemon IP: {daemon_ip}")
    else:
        daemon_ip = sys.argv[1]
    
    client = SimpClient(daemon_ip)
    client.start()


if __name__ == "__main__":
    main()
