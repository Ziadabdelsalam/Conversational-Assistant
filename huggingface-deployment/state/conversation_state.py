from typing import TypedDict, Annotated, Sequence, Optional
from models.schemas import ConversationContext, IntentType
import operator

class ConversationState(TypedDict):
    messages: Annotated[Sequence[str], operator.add]
    context: ConversationContext
    current_intent: Optional[IntentType]
    extracted_entities: dict
    missing_fields: list
    awaiting_confirmation: bool
    confirmation_message: str
    final_response: str