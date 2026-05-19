import asyncio
import json
import base64
import websockets


BROKER_URI = "ws://127.0.0.1:8001/broker"


async def test_storage_broker():
    async with websockets.connect(BROKER_URI) as ws:
        await ws.send(json.dumps({
            "action": "subscribe",
            "topic": "storage.ack"
        }))

        data = base64.b64encode(b"test_pres_broker").decode("utf-8")

        await ws.send(json.dumps({
            "action": "publish",
            "topic": "storage.write",
            "payload": {
                "object_id": "test-object-1",
                "data": data
            }
        }))

        while True:
            msg = await ws.recv()

            if isinstance(msg, bytes):
                msg = msg.decode()

            print("Prijata zprava:", msg)
 

if __name__ == "__main__":
    asyncio.run(test_storage_broker())