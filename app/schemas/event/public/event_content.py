# app/schemas/event/public/event_content.py

from typing import Any, Dict, List
from pydantic import BaseModel

class EventContentSchema(BaseModel):
    blocks: List[Dict[str, Any]]

