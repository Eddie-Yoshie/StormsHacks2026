from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import DateTime, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from vision.flags import DEFAULT_ACTIVE_FLAGS
from .database import base

class Device(base):
    __tablename__ = "devices"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    flags: Mapped[list[bool]] = mapped_column(JSON, nullable=False, default=list)
    # which vision events the camera's watchdog runs: [fall, dead, bathroom]
    active_flags: Mapped[list[bool]] = mapped_column(JSON, nullable=False, default=lambda: list(DEFAULT_ACTIVE_FLAGS))

class Event(base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)

class EventResponse(BaseModel):
  id: int
  camera_id: str
  timestamp: datetime
  event_type: str

  model_config = ConfigDict(from_attributes=True)

  @field_validator("timestamp")
  @classmethod
  def _assume_utc(cls, value: datetime) -> datetime:
    # MySQL DATETIME drops the offset; events are stored in UTC, so say so or browsers read it as local time.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
