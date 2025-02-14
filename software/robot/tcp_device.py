#!/usr/bin/env python3
import socket

# Replace 'your.server.ip.address' with the actual IP address of your Mac
HOST = '192.168.8.199'
PORT = 6666


def run_client():
    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"Connected to server at {HOST}:{PORT}")

        while True:
            # Receive the message from the server
            data = s.recv(1024)
            if not data:
                print("Server disconnected.")
                break
            print(f"Received from server: {data!r}")

            # Echo the received data back to the server
            s.sendall(data)


if __name__ == '__main__':
    run_client()
