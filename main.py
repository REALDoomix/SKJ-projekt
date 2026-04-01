from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Annotated
from datetime import datetime

from sqlalchemy import create_engine, String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, Session, sessionmaker

from support import *

import os, aiofiles, uuid

app = FastAPI()

# Database configuration
DATABASE_URL = "sqlite:///./files_database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
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


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.post("/files/upload")
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

    return {
        "id": file_record.id,
        "user_id": file_record.user_id,
        "filename": file_record.filename,
        "path": file_record.path,
        "size": file_record.size,
        "created_at": file_record.created_at
    }

@app.get("/files/{file_id}")
async def get_file(file_id: str, db: Session = Depends(get_db)):
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="Soubor nenalezen")
    
    if not os.path.exists(file_record.path):
        raise HTTPException(status_code=404, detail="Soubor na disku chybí")
        
    return FileResponse(path=file_record.path, filename=file_record.filename)


@app.delete("/files/{file_id}")
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