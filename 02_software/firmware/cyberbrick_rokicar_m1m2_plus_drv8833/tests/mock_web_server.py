"""Local HTTP/WebSocket stand-in for browser-only controller checks."""

import argparse
import asyncio
from pathlib import Path

from websockets.asyncio.server import serve
from websockets.http11 import Headers, Response


INDEX_PATH = Path(__file__).resolve().parents[1] / "index.html"
HEALTH = b'{"m":0,"a":0,"r":0,"d":0,"h":120000,"c":1,"g":[1000,1000,1000],"e":0,"x":"","q":0}'


def response(status, reason, content_type, body=b""):
    headers = Headers()
    headers["Content-Type"] = content_type
    headers["Content-Length"] = str(len(body))
    headers["Cache-Control"] = "no-store"
    return Response(status, reason, headers, body)


def process_request(_connection, request):
    if request.path == "/ws":
        return None
    if request.path.startswith("/health"):
        return response(200, "OK", "application/json", HEALTH)
    if request.path.startswith("/favicon"):
        return response(204, "No Content", "text/plain")
    return response(200, "OK", "text/html; charset=utf-8", INDEX_PATH.read_bytes())


async def handle_websocket(connection):
    count = 0
    try:
        async for message in connection:
            if not isinstance(message, bytes) or len(message) != 12:
                await connection.close(code=1003, reason="expected 12-byte binary command")
                return
            count += 1
    finally:
        print({"websocket_frames": count}, flush=True)


async def main(host, port):
    async with serve(
        handle_websocket,
        host,
        port,
        process_request=process_request,
        compression=None,
        ping_interval=None,
    ):
        print(f"mock controller listening on http://{host}:{port}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))
