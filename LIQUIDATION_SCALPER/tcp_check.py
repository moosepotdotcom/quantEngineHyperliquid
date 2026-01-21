
import socket
import ssl
import sys

hostname = 'api.hyperliquid.xyz'
port = 443
context = ssl.create_default_context()

print(f"Connecting to {hostname}:{port}...")
try:
    with socket.create_connection((hostname, port), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            print("Successfully connected!")
            print(f"Cipher: {ssock.cipher()}")
except Exception as e:
    print(f"Failed: {e}")
    sys.exit(1)
