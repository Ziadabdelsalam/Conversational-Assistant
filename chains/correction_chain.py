from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict
import json

class CorrectionChain:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.memory = ConversationBufferMemory(return_messages=True)
        
        self.correction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are helping a user correct their previous request.
            Previous entities: {previous_entities}
            
            The user now wants to make a change. Update the entities accordingly.
            Return the complete updated entities, not just the changes.
            
            Look for correction patterns like:
            - "actually make it X"
            - "change that to Y"
            - "no, I meant Z"
            """),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{input}")
        ])
        
    def process_correction(self, user_input: str, previous_entities: dict) -> dict:
        chain = self.correction_prompt | self.llm
        
        response = chain.invoke({
            "input": user_input,
            "previous_entities": json.dumps(previous_entities),
            "history": self.memory.chat_memory.messages
        })
        
        # Parse and return updated entities
        try:
            # Attempt to parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return previous_entities
    
    def detect_correction(self, message: str) -> bool:
        """Check if message contains correction intent"""
        correction_keywords = [
            'actually', 'wait', 'no,', 'change', 'make it', 
            'instead', 'correction', 'update', 'modify', 'sorry'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in correction_keywords)