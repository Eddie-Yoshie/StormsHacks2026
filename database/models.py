from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .database import base


class Device(base):
    __tablename__ = "devices"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    flags: Mapped[list[bool]] = mapped_column(JSON, nullable=False, default=list)

class DeviceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    flags: list[bool] = Field(default_factory=list)
