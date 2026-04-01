from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Annotated
from datetime import datetime
from pydantic import BaseModel

from sqlalchemy import create_engine, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, Session, sessionmaker

from support import *

import os, aiofiles, uuid

app = FastAPI()

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

# ==================== Database Configuration ====================

DATABASE_URL = "sqlite:///./files_database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo = True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
class Base(DeclarativeBase):
    pass

# File model
class FileRecord(Base):
    __tablename__ = "files"
    
    id: Mapped[str] = MappedColumn(String, primary_key=True)
    user_id: Mapped[str] = MappedColumn(String, index=True)
    filename: Mapped[str] = MappedColumn(String)
    path: Mapped[str] = MappedColumn(String)
    size: Mapped[int] = MappedColumn()
    created_at: Mapped[datetime] = MappedColumn(DateTime, default=datetime.utcnow)

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


@app.get("/items/{item_id}", response_model=ItemResponse)
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.post("/files/upload", response_model=FileInfoResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    user_id: Annotated[str, Form()],
    db: Session = Depends(get_db)):

    file_id = str(uuid.uuid4())

    user_dir = os.path.join(STORAGE_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)

    file_path = os.path.join(user_dir, file_id)

    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    file_size = len(content)
    
    # Save to database
    file_record = FileRecord(
        id=file_id,
        user_id=user_id,
        filename=file.filename,
        path=file_path,
        size=file_size,
        created_at=datetime.utcnow()
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    return file_record

@app.get("/files/{file_id}")
async def get_file(file_id: str, db: Session = Depends(get_db)):
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    
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

    db.delete(file_record)
    db.commit()

    return {"message": "soubor je fuč"}