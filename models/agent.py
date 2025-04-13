from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AgentSkill(BaseModel):
    """Represents a skill that an agent can perform."""
    
    id: str
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)

class AgentCapabilities(BaseModel):
    """Represents the capabilities of an agent."""
    
    streaming: bool = False
    file_upload: bool = False
    image_output: bool = False

class AgentCard(BaseModel):
    """Represents an AI agent card following the A2A protocol."""
    
    name: str
    description: str = ""
    url: str
    version: str = "1.0.0"
    defaultInputModes: List[str] = Field(default_factory=lambda: ["text/plain"])
    defaultOutputModes: List[str] = Field(default_factory=lambda: ["text/plain"])
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: List[AgentSkill] = Field(default_factory=list)
    
    def dict(self, **kwargs):
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "defaultInputModes": self.defaultInputModes,
            "defaultOutputModes": self.defaultOutputModes,
            "capabilities": self.capabilities.dict() if self.capabilities else {},
            "skills": [skill.dict() for skill in self.skills]
        }
        
    def model_dump(self, **kwargs):
        """Added for Pydantic v2 compatibility."""
        return self.dict(**kwargs) 