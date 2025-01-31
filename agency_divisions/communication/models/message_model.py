from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    STATUS_UPDATE = "status_update"
    QUERY = "query"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    SYSTEM = "system"

class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class Message(BaseModel):
    """
    Represents a message exchanged between agents in the agency.
    """
    model_config = ConfigDict(
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    id: str = Field(..., description="Unique identifier for the message")
    type: MessageType = Field(..., description="Type of message")
    sender_id: str = Field(..., description="ID of the sending agent")
    receiver_id: str = Field(..., description="ID of the receiving agent")
    subject: str = Field(..., description="Message subject")
    content: Dict[str, Any] = Field(..., description="Message content")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="Message priority")
    created_at: datetime = Field(default_factory=datetime.now, description="Message creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Message expiration timestamp")
    references: List[str] = Field(default_factory=list, description="Referenced message IDs")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def is_expired(self) -> bool:
        """Check if the message has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def add_reference(self, message_id: str) -> None:
        """Add a reference to another message"""
        if message_id not in self.references:
            self.references.append(message_id)

    def update_metadata(self, key: str, value: Any) -> None:
        """Update message metadata"""
        self.metadata[key] = value

    def model_dump(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return super().model_dump()

if __name__ == "__main__":
    # Test message creation
    test_message = Message(
        id="msg_001",
        type=MessageType.TASK_ASSIGNMENT,
        sender_id="agent_1",
        receiver_id="agent_2",
        subject="New Task Assignment",
        content={"task_id": "task_001", "description": "Process data"},
        priority=MessagePriority.HIGH,
        expires_at=datetime.now().replace(hour=23, minute=59, second=59)
    )

    print(f"Message created: {test_message.model_dump()}")
    print(f"Is expired: {test_message.is_expired()}")