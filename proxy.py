from socket import *
import sys
import threading
import os
import time

if len(sys.argv) <= 1:
    print('Usage: "python proxy.py <proxy_ip>"')
    sys.exit(2)

tcpSerSock = socket(AF_INET, SOCK_STREAM)
proxy_ip = sys.argv[1]
proxy_port = 8080
tcpSerSock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
tcpSerSock.bind((proxy_ip, proxy_port))
tcpSerSock.listen(20)

CACHE_DIR = "."
CACHE_EXPIRY = 60


def load_error_page(status_code):
    page_map = {
        502: ("502.html", "502 Bad Gateway"),
        504: ("504.html", "504 Gateway Timeout"),
    }
    if status_code in page_map:
        filename, status_text = page_map[status_code]
        try:
            with open(os.path.join("HTML", "status", filename), "rb") as f:
                body = f.read()
            header = f"HTTP/1.0 {status_text}\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
            return header.encode() + body
        except IOError:
            pass
    header = f"HTTP/1.0 {status_code} Error\r\nContent-Type: text/html\r\n\r\n"
    body = f"<html><body><h1>{status_code} Error</h1></body></html>\r\n"
    return header.encode() + body.encode()


def serve_from_cache(cache_path, tcpCliSock):
    with open(cache_path, "rb") as f:
        outputdata = f.read()
    tcpCliSock.sendall(outputdata)


def fetch_from_server(host_only, port_only, path, cache_path):
    c = socket(AF_INET, SOCK_STREAM)
    c.settimeout(5)

    try:
        c.connect((host_only, port_only))
        fileobj = c.makefile("rwb", 0)

        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host_only}\r\n"
            f"Connection: close\r\n\r\n"
        )
        fileobj.write(request.encode())
        fileobj.flush()

        response = b""
        while True:
            chunk = fileobj.read(4096)
            if not chunk:
                break
            response += chunk

        c.close()

        with open(cache_path, "wb") as f:
            f.write(response)

        return response

    except timeout:
        c.close()
        raise
    except Exception:
        c.close()
        raise


def handleClient(tcpCliSock, addr):
    start = time.time()
    print("Ready to serve...")
    print("Received a connection from:", addr)
    print()

    message = tcpCliSock.recv(4096).decode(errors="ignore")
    if not message:
        tcpCliSock.close()
        return

    print(message)

    raw_filename = message.split()[1].lstrip("/")

    if raw_filename.startswith("http://"):
        filename = raw_filename.replace("http://", "", 1)
    elif raw_filename.startswith("https://"):
        filename = raw_filename.replace("https://", "", 1)
    else:
        filename = raw_filename

    print("Raw filename:", filename)

    parts = filename.split("/", 1)
    hostn = parts[0]

    if len(parts) > 1:
        path = "/" + parts[1]
    else:
        path = "/"

    print("Host:Port =", hostn + ", Path =", path)

    cache_path = os.path.join(CACHE_DIR, filename.replace("/", "_").replace(":", "_"))
    print("Cache filename:", cache_path)

    cache_hit = False

    try:
        if os.path.exists(cache_path):
            age = time.time() - os.path.getmtime(cache_path)
            if age <= CACHE_EXPIRY:
                cache_hit = True
                print("Cache HIT (age: {:.1f}s)".format(age))
            else:
                os.remove(cache_path)
                print("Cache expired and removed:", cache_path)

        if cache_hit:
            serve_from_cache(cache_path, tcpCliSock)
            print("Read from cache -> HIT")
        else:
            print("Cache MISS")

            if ":" in hostn:
                host_only, port_only = hostn.split(":")
                port_only = int(port_only)
            else:
                host_only = hostn
                port_only = 80

            response = fetch_from_server(host_only, port_only, path, cache_path)
            tcpCliSock.sendall(response)
            print("Fetched from server -> MISS")

    except timeout:
        print("Connection timed out -> 504")
        tcpCliSock.sendall(load_error_page(504))

    except Exception as e:
        print("Connection failed:", e)
        try:
            tcpCliSock.sendall(load_error_page(502))
        except:
            pass

    elapsed = (time.time() - start) * 1000
    print(f"[{time.strftime('%H:%M:%S')}] {addr[0]} | {filename} | {'HIT' if cache_hit else 'MISS'} | {elapsed:.0f}ms")

    tcpCliSock.close()


print(f"Proxy server listening on {proxy_ip}:{proxy_port}")

while True:
    tcpCliSock, addr = tcpSerSock.accept()
    t = threading.Thread(target=handleClient, args=(tcpCliSock, addr))
    t.daemon = True
    t.start()

tcpSerSock.close()
