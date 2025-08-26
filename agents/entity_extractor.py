from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.utils.function_calling import convert_to_openai_function
from models.schemas import MeetingDetails, EmailDetails
from typing import Dict
from datetime import datetime, timedelta
import json
import re
class EntityExtractorAgent:
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(
            api_key=api_key,
            model_name=model_name,
            temperature=0
        )
        
    def extract_meeting_entities(self, text: str, context: Dict = None) -> MeetingDetails:
        """Extract meeting details using function calling"""
        
        current_date = datetime.now()
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract meeting details from the user's message. 
            
            CURRENT DATE AND TIME: {current_datetime}
            Day of week: {day_of_week}
            
            Parse dates relative to the current date:
            - "tomorrow" means {tomorrow}
            - "next Monday" means the Monday after today
            - "next week" means 7 days from today
            
            Parse times like '3pm', '15:00' into 24-hour format (HH:MM).
            Extract participant email addresses if mentioned.
            
            Previous context: {context}"""),
            ("user", "{input}")
        ])
        
        try:
            # Calculate relative dates
            tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Bind the schema as a function
            llm_with_tools = self.llm.bind_functions(
                functions=[convert_to_openai_function(MeetingDetails)],
                function_call={"name": "MeetingDetails"}
            )
            
            chain = extraction_prompt | llm_with_tools
            
            result = chain.invoke({
                "input": text,
                "context": json.dumps(context) if context else "None",
                "current_datetime": current_date.strftime("%Y-%m-%d %H:%M"),
                "day_of_week": current_date.strftime("%A"),
                "tomorrow": tomorrow
            })
            
            # Parse the function call arguments
            if result.additional_kwargs.get("function_call"):
                args = json.loads(result.additional_kwargs["function_call"]["arguments"])
                
                # Post-process dates using our parser
                from utils.datetime_parser import LLMDateTimeParser
                parser = LLMDateTimeParser(self.llm)
                
                # If date field contains relative expression, parse it
                if args.get("date") and not re.match(r'\d{4}-\d{2}-\d{2}', args["date"]):
                    parsed = parser.parse(args["date"])
                    args["date"] = parsed["date"]
                
                return MeetingDetails(**args)
        except Exception as e:
            print(f"Error extracting meeting entities: {e}")
        
        return MeetingDetails()
    
    def extract_email_entities(self, text: str, context: Dict = None) -> EmailDetails:
        """Extract email details using function calling"""
        
        current_date = datetime.now()
        
        extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract email details from the user's message.
            
            CURRENT DATE AND TIME: {current_datetime}
            
            Identify the recipient's email address and the message body.
            If a subject is mentioned, extract it too.
            If any date/time references are in the email body, keep them relative to {current_datetime}.
            
            Previous context: {context}"""),
            ("user", "{input}")
        ])
        
        try:
            llm_with_tools = self.llm.bind_functions(
                functions=[convert_to_openai_function(EmailDetails)],
                function_call={"name": "EmailDetails"}
            )
            
            chain = extraction_prompt | llm_with_tools
            
            result = chain.invoke({
                "input": text,
                "context": json.dumps(context) if context else "None",
                "current_datetime": current_date.strftime("%Y-%m-%d %H:%M")
            })
            
            if result.additional_kwargs.get("function_call"):
                args = json.loads(result.additional_kwargs["function_call"]["arguments"])
                return EmailDetails(**args)
        except Exception as e:
            print(f"Error extracting email entities: {e}")
        
        return EmailDetails()