CONVERSATIONAL ASSISTANT 
==========================================

A conversational assistant built with LangChain and GPT-4o-mini that can schedule meetings and send emails through natural language interaction.


FEATURES
--------

* Intent Classification: Automatically detects whether users want to schedule meetings, send emails, or just chat
* Entity Extraction: Intelligently extracts meeting details (title, date, time) and email information (recipient, body)
* Confirmation Flow: Always confirms actions before execution to prevent mistakes
* Correction Handling: Supports corrections like "actually make it 4pm instead"
* Natural Date/Time Parsing: Understands expressions like "tomorrow at 3pm" or "next Monday"
* State Management: Maintains conversation context throughout the interaction
* Clean UI: Modern Gradio interface with real-time context display


SETUP INSTRUCTIONS
------------------

1. Clone the repository
   git clone <repository-url>
   cd conversational-assistant

2. Create a virtual environment
   python -m venv venv

3. Activate the virtual environment
   - On Windows:
     venv\Scripts\activate
   - On macOS/Linux:
     source venv/bin/activate

4. Install dependencies
   pip install -r requirements.txt

5. Set up your OpenAI API key
   - Create a .env file in the project root
   - Add your OpenAI API key:
     OPENAI_API_KEY=your-api-key-here

6. Run the application
   python main.py

7. Open your browser
   Navigate to http://localhost:7860


USAGE EXAMPLES
--------------

Scheduling Meetings:
- "Book a meeting with Sara tomorrow at 3pm"
- "Schedule a project sync with the team next Monday at 10am"
- "Set up a call with John about the budget review"

Sending Emails:
- "Send an email to alice@example.com saying I'll be late"
- "Write an email to bob@company.com about the quarterly report"
- "Email the team about tomorrow's meeting cancellation"

Corrections:
- "Actually, make that 4pm instead"
- "Change the meeting to Wednesday"
- "No wait, send it to john@example.com instead"

General Chat:
- "Hello! How are you?"
- "What can you help me with?"
- "Thank you!"


PROJECT STRUCTURE
-----------------

project/
├── main.py                     # Main Gradio application
├── agents/
│   ├── intent_classifier.py   # Intent detection using GPT-4o-mini
│   ├── entity_extractor.py    # Entity extraction with function calling
│   └── dialog_agent.py        # Dialog flow management with LangGraph
├── chains/
│   ├── confirmation_chain.py  # Confirmation message generation
│   └── correction_chain.py    # Handle user corrections
├── models/
│   └── schemas.py             # Pydantic models for structured data
├── state/
│   └── conversation_state.py  # Conversation state management
├── executors/
│   └── action_executor.py     # Mock execution (saves to JSON)
├── utils/
│   └── datetime_parser.py     # Advanced date/time parsing
├── config.py                  # Configuration management
├── outbox/                    # JSON output directory (created automatically)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
└── README.md                  # Documentation


HOW IT WORKS
------------

1. Intent Classification: Each message is analyzed to determine if the user wants to schedule a meeting, send an email, or just chat
2. Entity Extraction: Relevant information is extracted using GPT-4o-mini's function calling capabilities
3. Validation: The system checks if all required information is present
4. Information Gathering: If information is missing, the assistant asks for it naturally
5. Confirmation: Before executing any action, the assistant asks for confirmation
6. Execution: Upon confirmation, the action is saved as JSON in the outbox directory


OUTPUT FORMAT
-------------

Actions are saved as JSON files in the outbox directory:

Meeting Example:
{
  "type": "meeting",
  "timestamp": "2025-01-27T10:30:00",
  "data": {
    "title": "Project Sync",
    "date": "2025-01-28",
    "time": "15:00",
    "participants": ["sara@example.com"]
  },
  "status": "scheduled"
}

Email Example:
{
  "type": "email",
  "timestamp": "2025-01-27T10:35:00",
  "data": {
    "recipient": "alice@example.com",
    "subject": "Meeting Update",
    "body": "I'll be late to the meeting"
  },
  "status": "sent"
}




WORKFLOW GRAPH
---------------
<img width="561" height="833" alt="Conversational Assistant  drawio" src="https://github.com/user-attachments/assets/09dc9af3-ddaa-45df-ae05-2271bb4cc3a6" />

TROUBLESHOOTING
---------------

* API Key Error: Make sure your OpenAI API key is correctly set in the .env file
* Import Errors: Ensure all dependencies are installed with pip install -r requirements.txt
* Port Already in Use: Change the port in main.py if 7860 is already occupied
* Module Not Found: Check that all directories have been created and files are in the correct locations
* Connection Error: Verify your internet connection and OpenAI API access


SYSTEM REQUIREMENTS
-------------------

* Python 3.8 or higher
* 4GB RAM minimum
* Internet connection (for OpenAI API calls)
* Modern web browser (Chrome, Firefox, Safari, Edge)


ENVIRONMENT VARIABLES
---------------------

Required:
* OPENAI_API_KEY: Your OpenAI API key for GPT-4o-mini access

Optional (can be modified in config.py):
* MODEL_NAME: Default is "gpt-4o-mini"
* TEMPERATURE: Default is 0.1 for consistent responses
* OUTBOX_PATH: Default is "./outbox" for saving actions

