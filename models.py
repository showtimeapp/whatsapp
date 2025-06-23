from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class User(BaseModel):
    wa_number: str
    name: Optional[str] = None

class Message(BaseModel):
    user: User
    message: str
    type: str  # "text", "image", "pdf"
    media_url: Optional[str] = None
    timestamp: datetime
    response: Optional[str] = None