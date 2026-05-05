from fastapi import FastAPI, WebSocket
import json
import msgpack
from manager import ConnectionManager

app = FastAPI()
manager = ConnectionManager()


@app.websocket("/broker")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive()

            use_msgpack = "bytes" in data

            if use_msgpack:
                message = msgpack.unpackb(data["bytes"])
            else:
                message = json.loads(data["text"])

            action = message.get("action")
            topic = message.get("topic")

            if action == "subscribe":
                manager.subscribe(websocket, topic)

                response = {"status": f"subscribed to {topic}"}

                if use_msgpack:
                    await websocket.send_bytes(msgpack.packb(response))
                else:
                    await websocket.send_text(json.dumps(response))

            elif action == "publish":
                payload = message.get("payload")

                await manager.publish(topic, {
                    "topic": topic,
                    "payload": payload
                }, use_msgpack)

    except:
        manager.disconnect(websocket)