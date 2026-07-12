import asyncio
import websockets

async def main():
    uri = "ws://127.0.0.1:8000/ws/stream/vizag_pattern"

    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        print(msg)

asyncio.run(main())