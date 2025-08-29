from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from models.schemas import IntentClassification, IntentType
from datetime import datetime
import json

class IntentClassifierAgent:
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            api_key=api_key,
            model_name=model_name,
            temperature=0.1
        )
        
        # Use structured output with Pydantic
        self.parser = PydanticOutputParser(pydantic_object=IntentClassification)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent classification expert. 
            
            Current date and time: {current_datetime}
            
            Analyze the user's message and classify it into one of these intents:
            
            1. schedule_meeting: User wants to book, schedule, or arrange a meeting/appointment/call
            2. send_email: User wants to send, write, or compose an email
            3. chitchat: General conversation, greetings, or anything else
            
            Also extract any relevant entities mentioned.
            
            {format_instructions}
            
            Be precise and consider the primary action the user wants to take."""),
            ("user", "{input}")
        ])
        
    def classify(self, user_input: str) -> IntentClassification:
        try:
            chain = self.prompt | self.llm | self.parser
            
            result = chain.invoke({
                "input": user_input,
                "format_instructions": self.parser.get_format_instructions(),
                "current_datetime": datetime.now().strftime("%Y-%m-%d %H:%M %A")
            })
            
            return result
        except Exception as e:
            # Fallback to chitchat if classification fails
            return IntentClassification(
                intent=IntentType.CHITCHAT,
                confidence=0.5,
                entities={}
            )