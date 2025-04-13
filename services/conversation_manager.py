from typing import List, Optional, Dict, Any
from models import Conversation, Message, Part
import uuid

class ConversationManager:
    """Manages conversations and their messages."""
    
    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
    
    def create_conversation(self, name: str = "") -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(name=name or f"Conversation {len(self.conversations) + 1}")
        self.conversations[conversation.id] = conversation
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.conversations.get(conversation_id)
    
    def list_conversations(self) -> List[Conversation]:
        """List all conversations."""
        return list(self.conversations.values())
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    def create_message(self, conversation_id: str, role: str, content: str) -> Message:
        """Create a new message in a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            # Create the conversation if it doesn't exist
            conversation = Conversation(id=conversation_id, name=f"Conversation {len(self.conversations) + 1}")
            self.conversations[conversation_id] = conversation
        
        message = Message(
            role=role,
            conversation_id=conversation_id
        )
        message.add_text(content)
        
        return message
    
    def add_message_to_conversation(self, message: Message) -> None:
        """Add a message to a conversation."""
        conversation_id = message.conversation_id
        if not conversation_id:
            raise ValueError("Message does not have a conversation_id")
        
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            # Create the conversation if it doesn't exist
            conversation = Conversation(id=conversation_id, name=f"Conversation {len(self.conversations) + 1}")
            self.conversations[conversation_id] = conversation
        
        conversation.messages.append(message)
    
    def list_messages(self, conversation_id: str) -> List[Message]:
        """List all messages in a conversation."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        return conversation.messages 