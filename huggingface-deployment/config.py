import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.MODEL_NAME = "gpt-4o-mini"
        self.TEMPERATURE = 0.1  # Low temperature for consistent intent classification
        self.MAX_RETRIES = 3
        # Get from environment variables (Hugging Face Secrets)
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required. Set it in Hugging Face Secrets.")
        
        self.OUTBOX_PATH = os.getenv("OUTBOX_PATH", "/app/outbox")
        
        # Create outbox directory if it doesn't exist
        if not os.path.exists(self.OUTBOX_PATH):
            os.makedirs(self.OUTBOX_PATH)
        

