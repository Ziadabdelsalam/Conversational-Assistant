import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict

class ActionExecutor:
    def __init__(self, outbox_path: str = "./outbox"):
        self.outbox_path = Path(outbox_path)
        self.outbox_path.mkdir(exist_ok=True)
        
    def execute_meeting(self, meeting_data: Dict) -> Dict:
        """Save meeting details to JSON file"""
        timestamp = datetime.now().isoformat()
        action = {
            "type": "meeting",
            "timestamp": timestamp,
            "data": meeting_data,
            "status": "scheduled"
        }
        
        filename = f"meeting_{timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = self.outbox_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(action, f, indent=2)
            
        return {
            "status": "success", 
            "file": str(filepath),
            "action": action
        }
    
    def execute_email(self, email_data: Dict) -> Dict:
        """Save email details to JSON file"""
        timestamp = datetime.now().isoformat()
        action = {
            "type": "email",
            "timestamp": timestamp,
            "data": email_data,
            "status": "sent"
        }
        
        filename = f"email_{timestamp.replace(':', '-').replace('.', '-')}.json"
        filepath = self.outbox_path / filename
        
        with open(filepath, 'w') as f:
            json.dump(action, f, indent=2)
            
        return {
            "status": "success",
            "file": str(filepath),
            "action": action
        }
    
    def get_recent_actions(self, limit: int = 5) -> list:
        """Retrieve recent actions from outbox"""
        actions = []
        
        try:
            files = sorted(self.outbox_path.glob("*.json"), key=os.path.getmtime, reverse=True)
            for file in files[:limit]:
                with open(file, 'r') as f:
                    actions.append(json.load(f))
        except Exception as e:
            print(f"Error reading recent actions: {e}")
        
        return actions