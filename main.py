from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import Annotated
from datetime import datetime
from pydantic import BaseModel
from starlette.requests import Request

from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal

from models import FileRecord, Bucket

from support import *

import os, aiofiles, uuid, websockets, json

app = FastAPI()
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
    image_path: str

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
    async with websockets.connect(BROKER_URI) as ws:
        await ws.send(json.dumps(message))


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

    file_path = os.path.join(bucket_dir, file_id)

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



@app.post("/process")
async def process(data: ProcessRequest):

    message = {
        "action": "publish",
        "topic": "image.jobs",
        "payload": {
            "operation": data.operation,
            "image_path": data.image_path
        }
    }

    await send_to_broker(message)

    return {"status": "processing_started"}