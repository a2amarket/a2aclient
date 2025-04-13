from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Tuple, Union
import uuid
from datetime import datetime

class Part(BaseModel):
    """Represents a part of a message, which can be text, data, or media."""
    
    type: str  # text, data, file
    content: Union[str, Dict[str, Any], bytes] = ""
    mime_type: str = "text/plain"
    
    def dict(self, **kwargs):
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "content": self.content,
            "mime_type": self.mime_type
        }
        
    def model_dump(self, **kwargs):
        """Added for Pydantic v2 compatibility."""
        return self.dict(**kwargs)

class Message(BaseModel):
    """Represents a message in a conversation."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # user, agent, system
    parts: List[Part] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    conversation_id: Optional[str] = None
    
    def add_text(self, text: str):
        """Add a text part to the message."""
        self.parts.append(Part(type="text", content=text, mime_type="text/plain"))
    
    def add_data(self, data: Dict[str, Any]):
        """Add a data part to the message."""
        self.parts.append(Part(type="data", content=data, mime_type="application/json"))
    
    def add_file(self, file: bytes, mime_type: str):
        """Add a file part to the message."""
        self.parts.append(Part(type="file", content=file, mime_type=mime_type))
    
    def dict(self, **kwargs):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "role": self.role,
            "parts": [part.dict() for part in self.parts],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "conversation_id": self.conversation_id
        }
        
    def model_dump(self, **kwargs):
        """Added for Pydantic v2 compatibility."""
        return self.dict(**kwargs) 