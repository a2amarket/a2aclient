from pydantic import BaseModel, Field
from typing import List, Optional
from .message import Message
import uuid
from datetime import datetime

class Conversation(BaseModel):
    """Represents a conversation between a user and one or more agents."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    is_active: bool = True
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    messages: List[Message] = Field(default_factory=list)
    
    def dict(self, **kwargs):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "messages": [msg.dict() for msg in self.messages]
        }
        
    def model_dump(self, **kwargs):
        """Added for Pydantic v2 compatibility."""
        return self.dict(**kwargs) 