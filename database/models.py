from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import base

class Device(base):
    __tablename__ = "devices"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    flags: Mapped[list[bool]] = mapped_column(JSON, nullable=False, default=list)
    active_flags: Mapped[list[bool]] = mapped_column(JSON, nullable=False, default=list)

class Event(base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_id: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

class EventResponse(BaseModel):
  id: int
  camera_id: int
  timestamp: datetime
  event_type: str

  model_config = ConfigDict(from_attributes=True)
