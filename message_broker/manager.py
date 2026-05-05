from fastapi import WebSocket
import msgpack
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def subscribe(self, websocket: WebSocket, topic: str):
        if topic not in self.active_connections:
            self.active_connections[topic] = set()

        self.active_connections[topic].add(websocket)

    def disconnect(self, websocket: WebSocket):
        for topic in self.active_connections:
            self.active_connections[topic].discard(websocket)

    async def publish(self, topic: str, message, use_msgpack=False):
        if topic not in self.active_connections:
            return

        dead_connections = []

        for connection in self.active_connections[topic]:
            try:
                if use_msgpack:
                    await connection.send_bytes(msgpack.packb(message))
                else:
                    await connection.send_text(json.dumps(message))
            except:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)