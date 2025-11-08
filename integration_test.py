import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

def handle_client(conn, addr):
    print(f"[+] Connected: {addr}")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"[{addr}] {data.decode(errors='ignore')}")
            conn.sendall(b"ACK")
    except Exception as e:
        print(f"[!] Error with {addr}: {e}")
    finally:
        conn.close()
        print(f"[-] Disconnected: {addr}")

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()

if __name__ == "__main__":
    main()
