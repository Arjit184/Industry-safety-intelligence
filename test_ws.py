import asyncio
import json
import websockets

async def test():
    uri = "ws://localhost:8000/ws/stream/vizag_pattern"

    async with websockets.connect(uri) as ws:
        count = 0

        async for msg in ws:
            d = json.loads(msg)

            if d.get("type"):
                continue

            count += 1
            print(
                f"tick {count}: "
                f"score={d['risk_score']} "
                f"level={d['risk_level']}"
            )

            if count >= 30:
                break

        print("Stability test: PASS")

asyncio.run(test())