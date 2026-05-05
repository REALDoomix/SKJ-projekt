import asyncio
import websockets
import json
import numpy as np
from PIL import Image

BROKER_URI = "ws://127.0.0.1:8001/broker"


# -----------------------
# IMAGE OPERATIONS
# -----------------------

def invert(img):
    return 255 - img


def mirror(img):
    return img[:, ::-1, :]


def crop(img):
    return img[100:-100, 100:-100, :]


def brighten(img):
    tmp = img.astype(np.int16) + 70
    return np.clip(tmp, 0, 255).astype(np.uint8)


def grayscale(img):
    r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
    gray = 0.299*r + 0.587*g + 0.114*b
    return np.stack([gray, gray, gray], axis=2).astype(np.uint8)


def process_image(operation, path):
    img = np.array(Image.open(path))

    if operation == "invert":
        result = invert(img)
    elif operation == "mirror":
        result = mirror(img)
    elif operation == "crop":
        result = crop(img)
    elif operation == "brighten":
        result = brighten(img)
    elif operation == "grayscale":
        result = grayscale(img)
    else:
        print("Neznámá operace")
        return

    output_path = "output_" + path
    Image.fromarray(result).save(output_path)

    print(f"Hotovo: {output_path}")


# -----------------------
# WORKER
# -----------------------

async def worker():
    async with websockets.connect(BROKER_URI) as ws:

        # subscribe
        await ws.send(json.dumps({
            "action": "subscribe",
            "topic": "image.jobs"
        }))

        print("Worker běží a čeká...")

        while True:
            msg = await ws.recv()

            if isinstance(msg, bytes):
                msg = msg.decode()

            data = json.loads(msg)

            payload = data.get("payload") or data

            operation = payload.get("operation")
            path = payload.get("image_path")

            if not operation or not path:
                print("Ignoruju špatnou zprávu:", payload)
                continue

            print("Přijato:", payload)

            process_image(operation, path)

            await ws.send(json.dumps({
                "action": "publish",
                "topic": "image.done",
                "payload": {
                    "status": "done",
                    "file": "output_" + path
                }
            }))

if __name__ == "__main__":
    asyncio.run(worker())