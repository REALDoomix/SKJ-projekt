from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import Annotated
from datetime import datetime
from pydantic import BaseModel
from starlette.requests import Request
import asyncio
from contextlib import asynccontextmanager

from fastapi.middleware.cors import CORSMiddleware


from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal

from models import FileRecord, Bucket


from support import *

import os, aiofiles, uuid, websockets, json

# Background task pro naslouchání na image.done
broker_listener_task = None


# ==================== LIFESPAN ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - spusť background task
    global broker_listener_task
    broker_listener_task = asyncio.create_task(listen_to_broker_results())
    print("Background task spusten")
    
    yield
    
    # Shutdown - zastavit background task
    if broker_listener_task:
        broker_listener_task.cancel()
        print("Background task zastaven")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BROKER_URI = "ws://127.0.0.1:8001/broker"


# ==================== Middleware ====================

@app.middleware("http")
async def count_requests(request: Request, call_next):
    """Middleware pro počítání API requestů"""
    response = await call_next(request)
    
    # Extrakt bucket_id z URL
    path_parts = request.url.path.split('/')
    bucket_id = None
    
    if 'buckets' in path_parts:
        idx = path_parts.index('buckets')
        if idx + 1 < len(path_parts):
            bucket_id = path_parts[idx + 1]
    
    # Inkrementuj počítadla pouze pro úspěšné requesty
    if bucket_id and 200 <= response.status_code < 300:
        db = SessionLocal()
        try:
            bucket = db.query(Bucket).filter(Bucket.id == bucket_id).first()
            if bucket:
                if request.method in ["POST", "PUT", "DELETE"]:
                    bucket.count_write_requests += 1
                elif request.method == "GET":
                    bucket.count_read_requests += 1
                db.commit()
        finally:
            db.close()
    
    return response


# ==================== Pydantic Models ====================

class FileInfoResponse(BaseModel):
    """Response model pro uploaded soubor"""
    id: str
    user_id: str
    filename: str
    path: str
    size: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeleteMessageResponse(BaseModel):
    """Response model pro smazaný soubor"""
    message: str


class RootResponse(BaseModel):
    """Response model pro root endpoint"""
    Hello: str


class ItemResponse(BaseModel):
    """Response model pro items endpoint"""
    item_id: int
    q: str | None = None

class BucketCreate(BaseModel):
    name: str


class BucketResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class BucketBillingResponse(BaseModel):
    bucket_id: str
    bandwidth_bytes: int


class BucketStatsResponse(BaseModel):
    """Response model pro statistiky bucketu"""
    id: str
    name: str
    created_at: datetime
    bandwidth_bytes: int
    count_read_requests: int
    count_write_requests: int

    class Config:
        from_attributes = True


class ProcessRequest(BaseModel):
    operation: str
    operation_params: dict | None = None

# Create tables
Base.metadata.create_all(bind=engine)

STORAGE_DIR = "storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_model=RootResponse)
def read_root():
    return {"Hello": "World"}

async def send_to_broker(message: dict):
    try:
        async with websockets.connect(BROKER_URI) as ws:
            await ws.send(json.dumps(message))
            print(f"[Gateway] Poslano do brokera: {message.get('topic')}")
    except Exception as e:
        print(f"[Gateway] Chyba pri poslani do brokera: {e}")


@app.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.post("/files/upload", response_model=FileInfoResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    user_id: Annotated[str, Form()],
    bucket_id: Annotated[str, Form()],
    db: Session = Depends(get_db)):

    file_id = str(uuid.uuid4())

    bucket = db.query(Bucket).filter(Bucket.id == bucket_id).first()

    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket neexistuje")

    bucket_dir = os.path.join(STORAGE_DIR, bucket_id)
    os.makedirs(bucket_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(bucket_dir, file_id + file_ext)

    '''file_path = os.path.join(bucket_dir, file_id)'''

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    file_size = len(content)
    bucket.bandwidth_bytes += file_size
    
    # Save to database
    file_record = FileRecord(
        id=file_id,
        user_id=user_id,
        filename=file.filename,
        path=file_path,
        size=file_size,
        created_at=datetime.utcnow(),
        bucket_id=bucket_id
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    return file_record

@app.get("/files/{file_id}")
async def get_file(file_id: str, db: Session = Depends(get_db)):
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

    if not file_record or file_record.is_deleted:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    
    bucket = db.query(Bucket).filter(Bucket.id == file_record.bucket_id).first()

    if bucket:
        bucket.bandwidth_bytes += file_record.size
        db.commit()
    
    if not os.path.exists(file_record.path):
        raise HTTPException(status_code=404, detail="Soubor na disku chybí")
        
    return FileResponse(path=file_record.path, filename=file_record.filename)


@app.delete("/files/{file_id}", response_model=DeleteMessageResponse)
def delete_file(file_id: str, user_id: str, db: Session = Depends(get_db)):
    
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")

    if file_record.user_id != user_id:
        raise HTTPException(status_code=403, detail="NEMAS PRISTUP DUPO")
    
    if os.path.exists(file_record.path):
        os.remove(file_record.path)

    file_record.is_deleted = True

    #db.delete(file_record)
    db.commit()

    return {"message": "soubor je fuč"}


@app.post("/buckets", response_model=BucketResponse)
def create_bucket(bucket: BucketCreate, db: Session = Depends(get_db)):
    
    existing = db.query(Bucket).filter(Bucket.name == bucket.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bucket s tímto jménem už existuje")

    new_bucket = Bucket(
        id=str(uuid.uuid4()),
        name=bucket.name,
        created_at=datetime.utcnow()
    )

    db.add(new_bucket)
    db.commit()
    db.refresh(new_bucket)

    return new_bucket

@app.get("/buckets/{bucket_id}/files", response_model=list[FileInfoResponse])
def get_files_in_bucket(bucket_id: str, db: Session = Depends(get_db)):

    bucket = db.query(Bucket).filter(Bucket.id == bucket_id).first()
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket neexistuje")

    files = db.query(FileRecord).filter(FileRecord.bucket_id == bucket_id,
                                        FileRecord.is_deleted == False).all()

    return files

@app.get("/buckets/{bucket_id}/billing", response_model=BucketBillingResponse)
def get_bucket_billing(bucket_id: str, db: Session = Depends(get_db)):

    bucket = db.query(Bucket).filter(Bucket.id == bucket_id).first()

    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket neexistuje")

    return {
        "bucket_id": bucket.id,
        "bandwidth_bytes": bucket.bandwidth_bytes or 0
    }


@app.get("/buckets/{bucket_id}/stats", response_model=BucketStatsResponse)
def get_bucket_stats(bucket_id: str, db: Session = Depends(get_db)):
    """Vrátí statistiky bucketu včetně počítadel requestů"""
    bucket = db.query(Bucket).filter(Bucket.id == bucket_id).first()
    
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket neexistuje")
    
    return bucket


@app.post("/buckets/{bucket_id}/objects/{file_id}/process")
async def process_object(
    bucket_id: str,
    file_id: str,
    request_data: ProcessRequest,
    db: Session = Depends(get_db)
):
    """S3 Gateway style endpoint pro zpracování obrázku"""
    
    # Ověř že soubor existuje
    file_record = db.query(FileRecord).filter(
        FileRecord.id == file_id,
        FileRecord.bucket_id == bucket_id,
        FileRecord.is_deleted == False
    ).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    
    # Okamžitě vrať odpověď
    message = {
        "action": "publish",
        "topic": "image.jobs",
        "payload": {
            "operation": request_data.operation,
            "image_path": file_record.path,
            "file_id": file_id,
            "bucket_id": bucket_id,
            "user_id": file_record.user_id,
            "operation_params": request_data.operation_params
        }
    }
    
    # Neblokuj - pošli do brokera v backgroundu
    asyncio.create_task(send_to_broker(message))
    
    return {"status": "processing_started"}


# ==================== BACKGROUND TASK PRO ZPRACOVANÉ OBRÁZKY ====================

async def listen_to_broker_results():
    """Background task, která naslouchá výsledky z image.done"""
    BROKER_URI = "ws://127.0.0.1:8001/broker"
    
    while True:
        try:
            print("[Gateway] Pripojuji se na broker...")
            async with websockets.connect(BROKER_URI) as ws:
                # Subscribe na výsledky
                await ws.send(json.dumps({
                    "action": "subscribe",
                    "topic": "image.done"
                }))
                
                print("[Gateway] Naslouchám na image.done...")
                
                while True:
                    msg = await ws.recv()
                    
                    if isinstance(msg, bytes):
                        msg = msg.decode()
                    
                    data = json.loads(msg)
                    payload = data.get("payload", data)
                    
                    # Kontrola povinných polí
                    file_id = payload.get("file_id")
                    bucket_id = payload.get("bucket_id")
                    user_id = payload.get("user_id")
                    operation = payload.get("operation")
                    status = payload.get("status")
                    
                    if not all([file_id, bucket_id, user_id, status]):
                        print(f"Ignoruju neuplnou zpravu: {payload}")
                        continue
                    
                    # Zpracuj error zprávy
                    if status == "error":
                        error_msg = payload.get("error", "Neznámá chyba")
                        print(f"Chyba z workeru: {file_id} - {operation}")
                        print(f"   Popis: {error_msg}")
                        continue
                    
                    # Zpracuj úspěšné zprávy
                    if status != "done":
                        print(f"Neznámý status: {status}")
                        continue
                    
                    output_path = payload.get("output_path")
                    if not output_path:
                        print(f"Zprava typu 'done' bez output_path: {payload}")
                        continue
                    
                    print(f"Prijato z image.done: {file_id} - {operation}")
                    
                    # Ulož do databáze
                    db = SessionLocal()
                    try:
                        # Vytvořit nový FileRecord pro zpracovaný obrázek
                        processed_file_id = str(uuid.uuid4())
                        
                        # Získej originální soubor pro info
                        original_file = db.query(FileRecord).filter(
                            FileRecord.id == file_id
                        ).first()
                        
                        if original_file:
                            # Získej velikost zpracovaného souboru
                            file_size = 0
                            if os.path.exists(output_path):
                                file_size = os.path.getsize(output_path)
                            
                            # Vytvoř nový FileRecord
                            processed_record = FileRecord(
                                id=processed_file_id,
                                user_id=user_id,
                                filename=f"{operation}_{original_file.filename}",
                                path=output_path,
                                size=file_size,
                                created_at=datetime.utcnow(),
                                bucket_id=bucket_id
                            )
                            
                            db.add(processed_record)
                            db.commit()
                            
                            print(f"Ulozeno zpracovane obrazky: {processed_file_id}")
                        else:
                            print(f"Originalni soubor {file_id} nebyl nalezen v DB")
                    except Exception as e:
                        print(f"Chyba pri ukladani do DB: {e}")
                        db.rollback()
                    finally:
                        db.close()
        
        except Exception as e:
            print(f"Chyba v broker listeneru: {e}")
            await asyncio.sleep(5)  # Počkej před reconnectem