from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class IntentType(str, Enum):
    SCHEDULE_MEETING = "schedule_meeting"
    SEND_EMAIL = "send_email"
    CHITCHAT = "chitchat"

class MeetingDetails(BaseModel):
    title: Optional[str] = Field(None, description="Title or purpose of the meeting")
    date: Optional[str] = Field(None, description="Date of the meeting")
    time: Optional[str] = Field(None, description="Time of the meeting")
    participants: Optional[List[str]] = Field(default_factory=list, description="Email addresses of participants")
    
    @validator('date', 'time', pre=True)
    def parse_datetime(cls, v):
        if v:
            return str(v)
        return v

class EmailDetails(BaseModel):
    recipient: Optional[str] = Field(None, description="Email address of recipient")
    subject: Optional[str] = Field(None, description="Email subject line")
    body: Optional[str] = Field(None, description="Email body content")
    
    @validator('recipient')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Invalid email address')
        return v

class IntentClassification(BaseModel):
    intent: IntentType
    confidence: float = Field(ge=0, le=1, description="Confidence score")
    entities: Optional[dict] = Field(default_factory=dict)
    
class ConversationContext(BaseModel):
    intent: Optional[IntentType] = None
    meeting_details: Optional[MeetingDetails] = None
    email_details: Optional[EmailDetails] = None
    state: Literal["idle", "collecting_info", "confirming", "executing", "completed"] = "idle"
    missing_fields: List[str] = Field(default_factory=list)
    confirmation_pending: bool = False
    raw_user_input: str = ""