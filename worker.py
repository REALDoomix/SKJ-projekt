import asyncio
import websockets
import json
import numpy as np
import os
from PIL import Image
import httpx
import tempfile

BROKER_URI = "ws://127.0.0.1:8001/broker"
GATEWAY_URL = "http://127.0.0.1:8000"

# -----------------------
# IMAGE OPERATIONS
# -----------------------

def invert(img):
    return 255 - img, None


def mirror(img):
    return img[:, ::-1, :], None


def crop(img, crop_params=None):
    """
    Ořízne obrázek na základě parametrů.
    
    crop_params: dict s keys 'top', 'left', 'bottom', 'right'
    """
    if crop_params is None:
        return img[100:-100, 100:-100, :], None
    
    try:
        top = int(crop_params['top'])
        left = int(crop_params['left'])
        bottom = int(crop_params['bottom'])
        right = int(crop_params['right'])
    except (ValueError, TypeError, KeyError):
        return None, "Chybné parametry pro crop. Vyžadováno: top, left, bottom, right (int)"
    
    img_height, img_width = img.shape[:2]
    
    if not (0 <= top < bottom <= img_height and 0 <= left < right <= img_width):
        return None, f"Parametry mimo rozsah obrázku ({img_width}x{img_height})"
    
    try:
        cropped = img[top:bottom, left:right, :]
        return cropped, None
    except Exception as e:
        return None, f"Chyba při oříznutí: {str(e)}"


def brighten(img):
    tmp = img.astype(np.int16) + 70
    return np.clip(tmp, 0, 255).astype(np.uint8), None


def grayscale(img):
    r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]
    gray = 0.299*r + 0.587*g + 0.114*b
    return np.stack([gray, gray, gray], axis=2).astype(np.uint8), None


def process_image(operation, img_array, operation_params=None):
    # zpracuje obrázek s vybranou operací
    if not operation:
        return None, "Operace není specifikována"
    
    operations_with_params = {
        "crop": lambda img: crop(img, operation_params.get('crop_params') if operation_params else None),
    }
    
    simple_operations = {
        "invert": invert,
        "mirror": mirror,
        "brighten": brighten,
        "grayscale": grayscale
    }

    try:
        if operation in operations_with_params:
            result, error = operations_with_params[operation](img_array)
            if error:
                return None, error
            return result, None
        
        elif operation in simple_operations:
            result, error = simple_operations[operation](img_array)
            if error:
                return None, error
            return result, None
        
        else:
            return None, f"Neznámá operace: {operation}"
    
    except Exception as e:
        return None, f"Chyba při zpracování operace {operation}: {str(e)}"


async def download_image(file_id):
    """Stáhne obrázek z Gateway přes API"""
    try:
        print(f"[Worker] Stahuji: {GATEWAY_URL}/files/{file_id}")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GATEWAY_URL}/files/{file_id}", timeout=10.0)
            print(f"[Worker] Response status: {response.status_code}")
            if response.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(response.content)
                    temp_path = tmp.name
                print(f"[Worker] Stazeno do: {temp_path}")
                return temp_path
            else:
                print(f"[Worker] Chyba stazeni: HTTP {response.status_code}")
                return None
    except Exception as e:
        print(f"[Worker] Vyjimka pri stahovani: {type(e).__name__}: {e}")
        return None


async def save_processed_image(bucket_id, file_id, img_array):
    """Uloží zpracovaný obrázek na disk"""
    try:
        bucket_dir = os.path.join("storage", bucket_id)
        os.makedirs(bucket_dir, exist_ok=True)
        
        # uložit s prefixem output
        output_filename = f"output_{file_id}.png"
        output_path = os.path.join(bucket_dir, output_filename)
        
        print(f"[Worker] Uklada se: {output_path}")
        Image.fromarray(img_array).save(output_path)
        print(f"[Worker] Ulozeno: {output_path}")
        return output_path
    except Exception as e:
        print(f"[Worker] Chyba pri ukladani: {e}")
        return None


# -----------------------
# WORKER
# -----------------------

async def worker():
    async with websockets.connect(BROKER_URI) as ws:

        # Subscribe na image.jobs
        await ws.send(json.dumps({
            "action": "subscribe",
            "topic": "image.jobs"
        }))

        print("[Worker] Spusten a ceka na zravy...")

        while True:
            msg = await ws.recv()

            if isinstance(msg, bytes):
                msg = msg.decode()

            data = json.loads(msg)
            print(f"[Worker] Prijata zprava: {data.get('action')} - {data.get('topic')}")
            
            payload = data.get("payload", data)

            # kontrola polí
            operation = payload.get("operation")
            file_id = payload.get("file_id")
            bucket_id = payload.get("bucket_id")
            user_id = payload.get("user_id")
            
            # Volitelné parametry pro operace (např. crop_params)
            operation_params = payload.get("operation_params")

            if not all([operation, file_id, bucket_id, user_id]):
                print(f"[Worker] Ignoruji zpravu - chybi pole: op={operation}, file={file_id}, bucket={bucket_id}, user={user_id}")
                continue

            print(f"[Worker] Zpracovavam: {operation} na {file_id}")

            # 1. Stáhni obrázek
            temp_path = await download_image(file_id)
            if not temp_path:
                print(f"[Worker] Chyba: Nelze stahout obrazek")
                error_msg = {
                    "action": "publish",
                    "topic": "image.done",
                    "payload": {
                        "status": "error",
                        "file_id": file_id,
                        "bucket_id": bucket_id,
                        "user_id": user_id,
                        "operation": operation,
                        "error": "Stahovani obrazku selhalo"
                    }
                }
                await ws.send(json.dumps(error_msg))
                print(f"[Worker] Odeslan error status")
                continue


            try:
                print(f"[Worker] Nacitam obrazek")
                img = np.array(Image.open(temp_path))
                print(f"[Worker] Obrazek nacten: {img.shape}")
            except Exception as e:
                print(f"[Worker] Chyba pri nacitani: {e}")
                os.remove(temp_path)
                # Pošli error zprávu
                error_msg = {
                    "action": "publish",
                    "topic": "image.done",
                    "payload": {
                        "status": "error",
                        "file_id": file_id,
                        "bucket_id": bucket_id,
                        "user_id": user_id,
                        "operation": operation,
                        "error": f"Nelze nacist obrazek: {str(e)}"
                    }
                }
                await ws.send(json.dumps(error_msg))
                continue


            print(f"[Worker] Zpracovavam operaci: {operation}")
            result_img, error = process_image(operation, img, operation_params)
            
            # Vyčisti temp soubor
            os.remove(temp_path)
            
            if error:
                print(f"[Worker] Chyba operace: {error}")
                error_msg = {
                    "action": "publish",
                    "topic": "image.done",
                    "payload": {
                        "status": "error",
                        "file_id": file_id,
                        "bucket_id": bucket_id,
                        "user_id": user_id,
                        "operation": operation,
                        "error": error
                    }
                }
                await ws.send(json.dumps(error_msg))
                print(f"[Worker] Odeslan error")
                continue

            # zpracovaný obrázek
            print(f"[Worker] Ukladam vysledek")
            output_path = await save_processed_image(bucket_id, file_id, result_img)

            if not output_path:
                print(f"[Worker] Chyba: Nelze ulozit")
                error_msg = {
                    "action": "publish",
                    "topic": "image.done",
                    "payload": {
                        "status": "error",
                        "file_id": file_id,
                        "bucket_id": bucket_id,
                        "user_id": user_id,
                        "operation": operation,
                        "error": "Nelze ulozit zpracovany obrazek"
                    }
                }
                await ws.send(json.dumps(error_msg))
                continue

            # zpráva o dokončení
            print(f"[Worker] Odesilan uspech: {output_path}")
            response_msg = {
                "action": "publish",
                "topic": "image.done",
                "payload": {
                    "status": "done",
                    "file_id": file_id,
                    "bucket_id": bucket_id,
                    "user_id": user_id,
                    "operation": operation,
                    "output_path": output_path
                }
            }
            
            await ws.send(json.dumps(response_msg))
            print(f"[Worker] Hotovo: {file_id}")


if __name__ == "__main__":
    asyncio.run(worker())