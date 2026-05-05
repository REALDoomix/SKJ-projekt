from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from models import FileRecord, Bucket

engine = create_engine("sqlite:///files_database.db")

with Session(engine) as session:
    print("--- Buckets ---")
    buckets = session.query(Bucket).all()
    for b in buckets:
        print(f"ID: {b.id}, Name: {b.name}")
    
    print("\n--- Files ---")
    files = session.query(FileRecord).all()
    for f in files:
        print(f"ID: {f.id}, Name: {f.filename}, Bucket: {f.bucket_id}, Path: {f.path}")
