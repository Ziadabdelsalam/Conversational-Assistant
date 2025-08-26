from langchain_openai import ChatOpenAI
from datetime import datetime, timedelta
from langchain.prompts import ChatPromptTemplate
from typing import Dict, Optional
import re

class LLMDateTimeParser:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.current_datetime = datetime.now()
        
        self.prompt = ChatPromptTemplate.from_template("""
        IMPORTANT: Use this as the current date and time for all calculations:
        Current date: {current_date}
        Current time: {current_time}
        Current day of week: {day_of_week}
        
        Parse this date/time expression into a specific date and time:
        Expression: "{expression}"
        
        Rules:
        - "tomorrow" means {tomorrow_date}
        - "today" means {current_date}
        - "next Monday" means the Monday after {current_date}
        - Calculate all relative dates from {current_date}
        
        Return ONLY in format: YYYY-MM-DD HH:MM
        If time is not specified, return only: YYYY-MM-DD
        
        Examples based on current date {current_date}:
        - "tomorrow at 3pm" -> {tomorrow_date} 15:00
        - "next week" -> {next_week_date}
        - "in 2 hours" -> {current_date} {two_hours_later}
        """)
        
    def get_relative_dates(self):
        """Calculate commonly used relative dates"""
        now = self.current_datetime
        tomorrow = now + timedelta(days=1)
        next_week = now + timedelta(weeks=1)
        two_hours_later = now + timedelta(hours=2)
        
        return {
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time": now.strftime("%H:%M"),
            "day_of_week": now.strftime("%A"),
            "tomorrow_date": tomorrow.strftime("%Y-%m-%d"),
            "next_week_date": next_week.strftime("%Y-%m-%d"),
            "two_hours_later": two_hours_later.strftime("%H:%M")
        }
        
    def parse(self, expression: str) -> Dict[str, str]:
        dates = self.get_relative_dates()
        
        chain = self.prompt | self.llm
        
        result = chain.invoke({
            "expression": expression,
            **dates
        })
        
        # Parse the response
        parsed_text = result.content.strip()
        
        # Split date and time if both present
        if " " in parsed_text:
            date_part, time_part = parsed_text.split(" ", 1)
            return {"date": date_part, "time": time_part}
        else:
            # Only date provided
            return {"date": parsed_text, "time": None}