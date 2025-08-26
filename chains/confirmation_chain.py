from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from models.schemas import IntentType
from datetime import datetime
from typing import Dict

class ConfirmationChain:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        
        self.confirmation_prompt = ChatPromptTemplate.from_template("""
        Generate a clear, friendly confirmation message for the user's request.
        
        Current date and time: {current_datetime}
        
        Intent: {intent}
        Details: {details}
        
        Format it as a yes/no question that clearly states what action will be taken.
        Be specific about all details so the user can verify everything is correct.
        Include the actual dates (not relative terms) in the confirmation.
        """)
        
    def generate_confirmation(self, intent: IntentType, details: dict) -> str:
        chain = self.confirmation_prompt | self.llm
        
        response = chain.invoke({
            "intent": intent.value,
            "details": self.format_details(intent, details),
            "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M %A")
        })
        
        return response.content
    
    def format_details(self, intent: IntentType, details: dict) -> str:
        # Include actual parsed dates in confirmation
        if intent == IntentType.SCHEDULE_MEETING:
            date_str = details.get('date', 'unspecified date')
            time_str = details.get('time', 'unspecified time')
            
            # Convert date to readable format if it's in YYYY-MM-DD format
            try:
                if date_str and '-' in date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    date_str = date_obj.strftime("%A, %B %d, %Y")
            except:
                pass
                
            return f"Meeting '{details.get('title')}' on {date_str} at {time_str}"
            
        elif intent == IntentType.SEND_EMAIL:
            return f"Email to {details.get('recipient')} with message: '{details.get('body')}'"
        
        return str(details)