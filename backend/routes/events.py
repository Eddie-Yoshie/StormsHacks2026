from fastapi import APIRouter

from backend.dependencies.database import SessionDependency
from database.models import Event, EventResponse

router = APIRouter(prefix="/events", tags=["events"])

@router.get("", response_model=list[EventResponse])
def get_events(db: SessionDependency) -> list[EventResponse]:
    events = db.query(Event).all()        
    return [EventResponse.model_validate(e) for e in events]