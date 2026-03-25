from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import Annotated

import os,json,aiofiles,uuid

from multipart import *

app = FastAPI()

STORAGE_DIR = "storage"
METADATA = "metadata.json"


os.makedirs(STORAGE_DIR, exist_ok=True)
if not os.path.exists(METADATA):
    with open(METADATA, "w") as f:
        json.dump({}, f)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.post("/files/upload")
async def upload_file(
    file: Annotated[UploadFile, File()],
    user_id: Annotated[str,Form()]):

    file_id = str(uuid.uuid4())

    user_dir = os.path.join(STORAGE_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, file_id)

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    file_size = len(content)
    metadata = {
        "id": file_id,
        "user_id": user_id,
        "filename": file.filename,
        "path": file_path,
        "size": file_size
    }

    with open(METADATA, "r+") as f:
        data = json.load(f)

        data[file_id] = metadata

        f.seek(0)
        json.dump(data, f, indent=2)


    return metadata

@app.get("/files/{file_id}")
async def get_file(file_id: str):
    with open(METADATA, "r") as f:
        data = json.load(f)

    if file_id not in data:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
        
    file_info = data[file_id]
    file_path = file_info["path"]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Soubor na disku chybí")
        
    return FileResponse(path=file_path, filename=file_info["filename"])