from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, MappedColumn
from datetime import datetime

from database import Base


class FileRecord(Base):
    __tablename__ = "files"
    
    id: Mapped[str] = MappedColumn(String, primary_key=True)
    user_id: Mapped[str] = MappedColumn(String, index=True)
    filename: Mapped[str] = MappedColumn(String)
    path: Mapped[str] = MappedColumn(String)
    size: Mapped[int] = MappedColumn()
    created_at: Mapped[datetime] = MappedColumn(DateTime, default=datetime.utcnow)

    is_deleted: Mapped[bool] = MappedColumn(Boolean, default=False)

    bucket_id: Mapped[str] = MappedColumn(String, ForeignKey("buckets.id"))


class Bucket(Base):
    __tablename__ = "buckets"

    id: Mapped[str] = MappedColumn(String, primary_key=True)
    name: Mapped[str] = MappedColumn(String, unique=True)
    created_at: Mapped[datetime] = MappedColumn(DateTime, default=datetime.utcnow)
    bandwidth_bytes: Mapped[int] = MappedColumn(default=0)

    count_read_requests: Mapped[int] = MappedColumn(Integer, default=0)
    count_write_requests: Mapped[int] = MappedColumn(Integer, default=0)
