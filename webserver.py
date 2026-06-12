from socket import *
import sys
import threading
import os
import time

serverSocket = socket(AF_INET, SOCK_STREAM)
serverPort = 8000
serverSocket.bind(('0.0.0.0', serverPort))
serverSocket.listen(5)

udpSocket = socket(AF_INET, SOCK_DGRAM)
udpPort = 9000
udpSocket.bind(('0.0.0.0', udpPort))

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".mp4": "video/mp4",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
}

DOC_ROOT = "HTML"

TEXT_EXTENSIONS = {".html", ".css", ".js", ".svg", ".txt"}


def load_error_page(filename):
    try:
        with open(os.path.join(DOC_ROOT, "status", filename), "rb") as f:
            return f.read()
    except IOError:
        return None


def handleTCPClient(connectionSocket, addr):
    try:
        message = connectionSocket.recv(1024).decode(errors="ignore")
        if not message:
            connectionSocket.close()
            return

        print(f"[{time.strftime('%H:%M:%S')}] Connection from {addr}")

        for line in message.splitlines():
            print(line)
        print()

        parts = message.split()
        if len(parts) < 2:
            connectionSocket.close()
            return

        raw_filename = parts[1]

        if ".." in raw_filename:
            connectionSocket.send(
                "HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\n\r\n".encode()
            )
            connectionSocket.send(
                b"<html><body><h1>400 Bad Request</h1></body></html>\r\n"
            )
            print(f"[{time.strftime('%H:%M:%S')}] Rejected path with '..': {raw_filename} -> 400")
            connectionSocket.close()
            return

        clean_path = raw_filename[1:]
        if clean_path.startswith("HTML/"):
            clean_path = clean_path[5:]
        filepath = DOC_ROOT + "/" + clean_path

        _, ext = os.path.splitext(filepath)
        content_type = CONTENT_TYPES.get(ext, "application/octet-stream")
        is_text = ext in TEXT_EXTENSIONS

        try:
            if is_text:
                with open(filepath, encoding="utf-8") as f:
                    outputdata = f.read()
                connectionSocket.send(
                    f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n".encode()
                )
                for char in outputdata:
                    connectionSocket.send(char.encode())
                connectionSocket.send("\r\n".encode())
            else:
                with open(filepath, "rb") as f:
                    outputdata = f.read()
                header = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {len(outputdata)}\r\n"
                    f"\r\n"
                )
                connectionSocket.send(header.encode() + outputdata)

            print(f"[{time.strftime('%H:%M:%S')}] Served: {filepath} -> 200 OK")

        except IOError:
            body = load_error_page("404.html")
            if body is None:
                body = b"<html><body><h1>404 Not Found</h1></body></html>\r\n"
            connectionSocket.send(
                b"HTTP/1.1 404 Not Found\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"\r\n"
            )
            connectionSocket.sendall(body)
            print(f"[{time.strftime('%H:%M:%S')}] File not found: {filepath} -> 404")

    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error handling {addr}: {e}")
        try:
            body = load_error_page("500.html")
            if body is None:
                body = b"<html><body><h1>500 Internal Server Error</h1></body></html>\r\n"
            connectionSocket.send(
                b"HTTP/1.1 500 Internal Server Error\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"\r\n"
            )
            connectionSocket.sendall(body)
        except:
            pass

    finally:
        connectionSocket.close()


def handleUDPEcho():
    print(f"UDP Echo Server running on port {udpPort}")
    while True:
        try:
            data, addr = udpSocket.recvfrom(1024)
            print(f"[{time.strftime('%H:%M:%S')}] UDP echo from {addr}: {data.decode(errors='ignore')}")
            udpSocket.sendto(data, addr)
        except:
            pass


udpThread = threading.Thread(target=handleUDPEcho, daemon=True)
udpThread.start()

print(f"Web Server running on TCP port {serverPort} and UDP port {udpPort}")

while True:
    connectionSocket, addr = serverSocket.accept()
    clientThread = threading.Thread(target=handleTCPClient, args=(connectionSocket, addr))
    clientThread.daemon = True
    clientThread.start()

serverSocket.close()
