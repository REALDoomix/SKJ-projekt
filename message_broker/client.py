import asyncio
import websockets
import json
import msgpack

URI = "ws://127.0.0.1:8001/broker"


async def subscriber(use_msgpack):
    async with websockets.connect(URI) as ws:
        await ws.send(encode({
            "action": "subscribe",
            "topic": "news"
        }, use_msgpack))

        while True:
            msg = await ws.recv()

            decoded = decode(msg, use_msgpack)
            print("Dostal zprávu:", decoded)


async def publisher(use_msgpack):
    async with websockets.connect(URI) as ws:
        while True:
            text = input("Zpráva: ")

            message = {
                "action": "publish",
                "topic": "news",
                "payload": text
            }

            await ws.send(encode(message, use_msgpack))

def encode(data, use_msgpack):
    if use_msgpack:
        return msgpack.packb(data)
    else:
        return json.dumps(data)


def decode(data, use_msgpack):
    if use_msgpack:
        return msgpack.unpackb(data)
    else:
        return json.loads(data)


if __name__ == "__main__":
    mode = input("mode (sub/pub): ")
    fmt = input("format (json/msgpack): ")

    use_msgpack = fmt == "msgpack"

    if mode == "sub":
        asyncio.run(subscriber(use_msgpack))
    else:
        asyncio.run(publisher(use_msgpack))