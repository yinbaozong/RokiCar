"""Hardware-in-the-loop WebSocket stress test for OmniCar.

Default commands are zero speed, so it can safely exercise the real radio and
server path before enabling motors. Use non-zero values only with the car lifted.
"""

import argparse
import base64
import os
import socket
import struct
import time
import urllib.request

HOST = "192.168.4.1"
PORT = 80
DRIVE = 1
STOP = 2


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        block = sock.recv(size - len(data))
        if not block:
            raise ConnectionError("socket closed")
        data.extend(block)
    return bytes(data)


def read_headers(sock):
    data = bytearray()
    while b"\r\n\r\n" not in data:
        block = sock.recv(128)
        if not block:
            raise ConnectionError("socket closed during handshake")
        data.extend(block)
        if len(data) > 1024:
            raise ValueError("oversized handshake")
    return bytes(data)


def send_frame(sock, payload):
    mask = os.urandom(4)
    masked = bytes(value ^ mask[index & 3] for index, value in enumerate(payload))
    sock.sendall(b"\x82" + bytes((0x80 | len(payload),)) + mask + masked)


def send_close(sock):
    mask = os.urandom(4)
    sock.sendall(b"\x88\x80" + mask)


def read_frame(sock):
    first, second = read_exact(sock, 2)
    length = second & 0x7F
    if length >= 126:
        raise ValueError("unexpected long frame")
    return first & 0x0F, read_exact(sock, length)


def connect():
    sock = socket.create_connection((HOST, PORT), timeout=3)
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        "GET /ws HTTP/1.1\r\n"
        "Host: 192.168.4.1\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Key: " + key + "\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    ).encode()
    sock.sendall(request)
    reply = read_headers(sock)
    if b"101 Switching Protocols" not in reply:
        raise RuntimeError(reply.decode("utf-8", "replace"))
    sock.settimeout(0.02)
    return sock


def command(msg_type, sequence, vx=0, vy=0, rot=0):
    return struct.pack("<BBIhhh", 1, msg_type, sequence, vx, vy, rot)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=60)
    parser.add_argument("--hz", type=float, default=10)
    parser.add_argument("--vx", type=int, default=0)
    parser.add_argument("--vy", type=int, default=0)
    parser.add_argument("--rot", type=int, default=0)
    args = parser.parse_args()
    sock = connect()
    period = 1 / args.hz
    sequence = 0
    sent = failures = 0
    started = time.monotonic()
    next_send = started
    try:
        while time.monotonic() - started < args.duration:
            now = time.monotonic()
            if now >= next_send:
                sequence += 1
                send_frame(sock, command(DRIVE, sequence, args.vx, args.vy, args.rot))
                sent += 1
                next_send += period
            while True:
                try:
                    opcode, payload = read_frame(sock)
                except TimeoutError:
                    break
                except socket.timeout:
                    break
                except Exception:
                    failures += 1
                    break
            time.sleep(0.002)
        sequence += 1
        send_frame(sock, command(STOP, sequence))
        send_close(sock)
        time.sleep(0.25)
    finally:
        sock.close()
    print({"sent": sent, "failures": failures})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    health = opener.open("http://192.168.4.1/health", timeout=3).read().decode()
    print({"sent": sent, "failures": failures, "health": health})


if __name__ == "__main__":
    main()
