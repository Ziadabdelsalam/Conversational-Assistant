import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.1  # Low temperature for consistent intent classification
    MAX_RETRIES = 3
    OUTBOX_PATH = "./outbox"