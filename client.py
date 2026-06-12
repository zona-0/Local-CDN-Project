#!/usr/bin/env python3
from socket import *
import sys
import time

WEBSERVER_HOST = "172.20.10.4"
WEBSERVER_PORT = 8000


def mode_tcp(proxy_host, proxy_port, path):
    try:
        clientSocket = socket(AF_INET, SOCK_STREAM)
        clientSocket.connect((proxy_host, proxy_port))

        url = f"http://{WEBSERVER_HOST}:{WEBSERVER_PORT}{path}"
        request = (
            f"GET {url} HTTP/1.0\r\n"
            f"Host: {proxy_host}\r\n"
            f"Connection: close\r\n\r\n"
        )
        clientSocket.send(request.encode())

        response = b""
        while True:
            chunk = clientSocket.recv(4096)
            if not chunk:
                break
            response += chunk

        print(response.decode("utf-8", errors="replace"))
        clientSocket.close()

    except Exception as e:
        print("Error:", e)


def mode_udp(server_host, server_port=9000):
    try:
        clientSocket = socket(AF_INET, SOCK_DGRAM)
        clientSocket.settimeout(1.0)

        num_packets = 10
        rtts = []
        lost = 0

        for seq in range(1, num_packets + 1):
            timestamp = time.time()
            message = f"Ping {seq} {timestamp}"

            try:
                clientSocket.sendto(message.encode(), (server_host, server_port))
                data, addr = clientSocket.recvfrom(1024)
                rtt = (time.time() - timestamp) * 1000
                rtts.append(rtt)
                print(f"Ping {seq} RTT={rtt:.2f} ms")

            except timeout:
                lost += 1
                print(f"Ping {seq} Request timed out")

        total_sent = len(rtts) + lost
        loss_pct = (lost / total_sent) * 100 if total_sent > 0 else 0

        print()
        print("--- QoS Statistics ---")
        print(f"Packets Sent: {num_packets}")
        print(f"Packets Received: {len(rtts)}")
        print(f"Packet Loss: {loss_pct:.1f}%")

        if rtts:
            min_rtt = min(rtts)
            max_rtt = max(rtts)
            avg_rtt = sum(rtts) / len(rtts)

            if len(rtts) > 1:
                diffs = [rtts[i] - rtts[i - 1] for i in range(1, len(rtts))]
                jitter = (sum(d * d for d in diffs) / len(diffs)) ** 0.5
            else:
                jitter = 0.0

            print(f"RTT (ms): min={min_rtt:.2f}, avg={avg_rtt:.2f}, max={max_rtt:.2f}")
            print(f"Jitter (ms): {jitter:.2f}")
        else:
            print("No responses received")

        clientSocket.close()

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    USAGE = (
        "Usage:\n"
        "  python client.py -mode tcp <proxy_host> <proxy_port> <path>\n"
        "  python client.py -mode udp <server_host> [server_port]"
    )

    if len(sys.argv) < 3:
        print(USAGE)
        sys.exit(2)

    mode_idx = 2 if sys.argv[1] == "-mode" else 1
    mode = sys.argv[mode_idx]
    args = sys.argv[mode_idx + 1:]

    if mode == "tcp":
        if len(args) < 3:
            print("Usage: python client.py -mode tcp <proxy_host> <proxy_port> <path>")
            sys.exit(2)
        mode_tcp(args[0], int(args[1]), args[2])

    elif mode == "udp":
        if len(args) < 1:
            print("Usage: python client.py -mode udp <server_host> [server_port]")
            sys.exit(2)
        server_port = int(args[1]) if len(args) > 1 else 9000
        mode_udp(args[0], server_port)

    else:
        print(f"Unknown mode: {mode}")
        print(USAGE)
        sys.exit(2)
