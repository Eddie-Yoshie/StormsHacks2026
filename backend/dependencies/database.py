from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from database.database import get_db

SessionDependency = Annotated[Session, Depends(get_db)]