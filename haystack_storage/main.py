import os, asyncio, json, websockets, base64
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

app = FastAPI(title="Haystack Storage Node")

VOLUMES_DIR = "haystack_storage/volumes"
MAX_VOLUME_SIZE = 100 * 1024 * 1024
BROKER_URI = "ws://127.0.0.1:8001/broker"

current_volume_id = 1


def get_volume_path(volume_id: int) -> str:
    return os.path.join(VOLUMES_DIR, f"volume_{volume_id}.dat")


def ensure_volumes_dir():
    os.makedirs(VOLUMES_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_event():
    ensure_volumes_dir()

    first_volume = get_volume_path(current_volume_id)
    if not os.path.exists(first_volume):
        open(first_volume, "ab").close()

    print("Haystack Storage Node spuštěn")
    print(f"Aktuální volume: {first_volume}")

    asyncio.create_task(listen_to_storage_write())


@app.get("/")
async def root():
    return {
        "service": "Haystack Storage Node",
        "status": "running",
        "current_volume_id": current_volume_id
    }


@app.post("/volume/write")
async def write_to_volume(request: Request):
    data = await request.body()
    result = write_bytes_to_volume(data)
    return result


@app.get("/volume/{volume_id}/{offset}/{size}")
async def read_from_volume(volume_id: int, offset: int, size: int):
    volume_path = get_volume_path(volume_id)

    if not os.path.exists(volume_path):
        raise HTTPException(status_code=404, detail="Volume neexistuje")

    with open(volume_path, "rb") as file:
        file.seek(offset)
        data = file.read(size)

    return Response(content=data, media_type="application/octet-stream")

def write_bytes_to_volume(data: bytes):
    global current_volume_id

    ensure_volumes_dir()

    volume_path = get_volume_path(current_volume_id)

    if not os.path.exists(volume_path):
        open(volume_path, "ab").close()

    current_size = os.path.getsize(volume_path)

    if current_size + len(data) > MAX_VOLUME_SIZE:
        current_volume_id += 1
        volume_path = get_volume_path(current_volume_id)
        open(volume_path, "ab").close()

    with open(volume_path, "ab") as file:
        offset = file.tell()
        file.write(data)
        size = len(data)

    return {
        "volume_id": current_volume_id,
        "offset": offset,
        "size": size
    }

async def listen_to_storage_write():
    while True:
        try:
            print("[Haystack] Pripojuji se k brokeru...")

            async with websockets.connect(BROKER_URI) as ws:
                await ws.send(json.dumps({
                    "action": "subscribe",
                    "topic": "storage.write"
                }))

                print("[Haystack] Posloucham topic storage.write")

                while True:
                    msg = await ws.recv()

                    if isinstance(msg, bytes):
                        msg = msg.decode()

                    message = json.loads(msg)
                    payload = message.get("payload", message)

                    object_id = payload.get("object_id")
                    encoded_data = payload.get("data")

                    if not object_id or not encoded_data:
                        print("[Haystack] Ignoruji zpravu bez object_id nebo data")
                        continue

                    file_data = base64.b64decode(encoded_data)

                    result = write_bytes_to_volume(file_data)

                    ack_message = {
                        "action": "publish",
                        "topic": "storage.ack",
                        "payload": {
                            "object_id": object_id,
                            "volume_id": result["volume_id"],
                            "offset": result["offset"],
                            "size": result["size"]
                        }
                    }

                    await ws.send(json.dumps(ack_message))

                    print(f"[Haystack] Ulozeno object_id={object_id}, volume={result['volume_id']}, offset={result['offset']}, size={result['size']}")

        except Exception as e:
            print(f"[Haystack] Chyba spojeni s brokerem: {e}")
            print("[Haystack] Zkusim znovu za 3 sekundy...")
            await asyncio.sleep(3)