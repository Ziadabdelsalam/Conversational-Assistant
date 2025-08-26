from datetime import datetime, timedelta
from typing import Dict, Optional

class DateContext:
    """Provides current date/time context for the LLM"""
    
    @staticmethod
    def get_context_string() -> str:
        """Get a formatted string with current date/time context"""
        now = datetime.now()
        
        context = f"""
        Current Information:
        - Date: {now.strftime('%Y-%m-%d')}
        - Time: {now.strftime('%H:%M')}
        - Day: {now.strftime('%A')}
        - Full: {now.strftime('%A, %B %d, %Y at %I:%M %p')}
        """
        
        return context.strip()
    
    @staticmethod
    def parse_relative_date(expression: str) -> Optional[str]:
        """Parse common relative date expressions without LLM"""
        now = datetime.now()
        expression_lower = expression.lower().strip()
        
        # Simple rule-based parsing for common cases
        if expression_lower == "today":
            return now.strftime("%Y-%m-%d")
        elif expression_lower == "tomorrow":
            return (now + timedelta(days=1)).strftime("%Y-%m-%d")
        elif expression_lower == "yesterday":
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif "next week" in expression_lower:
            return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")
        elif "next month" in expression_lower:
            # Approximate - add 30 days
            return (now + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Day of week parsing
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, day in enumerate(days):
            if day in expression_lower:
                current_day = now.weekday()
                days_ahead = i - current_day
                
                if "next" in expression_lower:
                    # Next occurrence (not this week)
                    if days_ahead <= 0:
                        days_ahead += 7
                    days_ahead += 7
                else:
                    # This week's occurrence
                    if days_ahead <= 0:
                        days_ahead += 7
                
                return (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        return None
    
    @staticmethod
    def parse_relative_time(expression: str) -> Optional[str]:
        """Parse common relative time expressions"""
        now = datetime.now()
        expression_lower = expression.lower().strip()
        
        # Handle "in X hours"
        if "hour" in expression_lower:
            import re
            match = re.search(r'(\d+)\s*hour', expression_lower)
            if match:
                hours = int(match.group(1))
                future_time = now + timedelta(hours=hours)
                return future_time.strftime("%H:%M")
        
        # Handle "in X minutes"
        if "minute" in expression_lower:
            import re
            match = re.search(r'(\d+)\s*minute', expression_lower)
            if match:
                minutes = int(match.group(1))
                future_time = now + timedelta(minutes=minutes)
                return future_time.strftime("%H:%M")
        
        # Handle standard times
        import re
        time_match = re.search(r'(\d{1,2})\s*([ap]m)', expression_lower)
        if time_match:
            hour = int(time_match.group(1))
            period = time_match.group(2)
            
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
                
            return f"{hour:02d}:00"
        
        return None