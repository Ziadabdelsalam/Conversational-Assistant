from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import json
import uuid
from datetime import datetime
import os

# Import your existing modules
from agents.intent_classifier import IntentClassifierAgent
from agents.entity_extractor import EntityExtractorAgent
from agents.dialog_agent import DialogAgent
from chains.confirmation_chain import ConfirmationChain
from chains.correction_chain import CorrectionChain
from executors.action_executor import ActionExecutor
from state.conversation_state import ConversationContext
from config import Config

app = FastAPI(
    title="AI Assistant API", 
    version="1.0.0",
    docs_url="/docs",  # Swagger UI available at /docs
    redoc_url="/redoc"  # ReDoc available at /redoc
)

# Enable CORS for mobile app - IMPORTANT!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for mobile app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = Config()
dialog_agent = DialogAgent(config.OPENAI_API_KEY)
executor = ActionExecutor(config.OUTBOX_PATH)
confirmation_chain = ConfirmationChain(dialog_agent.llm)
correction_chain = CorrectionChain(dialog_agent.llm)

# Store session states
session_states = {}

# [Keep all your existing models and endpoints exactly as they are]

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    intent: str
    entities: Dict
    state: str
    action_result: Optional[Dict] = None
    requires_confirmation: bool = False
    suggestions: List[str] = []

class SessionInfo(BaseModel):
    session_id: str
    created_at: str
    message_count: int
    last_intent: Optional[str]
    state: str

class ActionConfirmation(BaseModel):
    session_id: str
    confirmed: bool


@app.get("/")
async def root():
    return {
        "message": "AI Assistant API", 
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/chat",
            "confirm": "/confirm-action",
            "session": "/session/{session_id}",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    try:
        # Get or create session state
        if request.session_id not in session_states:
            session_states[request.session_id] = {
                "context": ConversationContext(),
                "awaiting_confirmation": False,
                "extracted_entities": {},
                "last_intent": None,
                "history": [],
                "created_at": datetime.now().isoformat(),
                "message_count": 0
            }
        
        session = session_states[request.session_id]
        session["message_count"] += 1
        
        # Add current date context
        current_date = datetime.now()
        enhanced_message = f"[Current date: {current_date.strftime('%Y-%m-%d %H:%M %A')}]\n{request.message}"
        
        # Process message through dialog agent
        result = dialog_agent.graph.invoke({
            "messages": [enhanced_message],
            "context": session["context"].to_dict()
        })
        
        # Extract response
        response_text = result["messages"][-1]
        if hasattr(response_text, 'content'):
            response_text = response_text.content
        
        # Update session
        session["history"].append({
            "user": request.message,
            "bot": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Determine current state
        state = "idle"
        requires_confirmation = False
        action_result = None
        suggestions = []
        
        # Check if awaiting confirmation
        if session["awaiting_confirmation"]:
            state = "awaiting_confirmation"
            requires_confirmation = True
            suggestions = ["Yes, confirm", "No, cancel", "Let me change something"]
        
        # Check for intent and entities
        intent_result = dialog_agent.intent_classifier.classify(request.message)
        entities = {}
        
        if intent_result.intent.value == "schedule_meeting":
            entities = dialog_agent.entity_extractor.extract_meeting_entities(
                request.message, 
                session["context"].to_dict()
            ).dict()
            state = "gathering_meeting_info"
            
            # Check if we have all required info
            if entities.get("title") and entities.get("date") and entities.get("time"):
                state = "ready_to_confirm"
                requires_confirmation = True
                
        elif intent_result.intent.value == "send_email":
            entities = dialog_agent.entity_extractor.extract_email_entities(
                request.message,
                session["context"].to_dict()
            ).dict()
            state = "gathering_email_info"
            
            if entities.get("recipient") and entities.get("body"):
                state = "ready_to_confirm"
                requires_confirmation = True
        
        # Store extracted entities
        if entities:
            session["extracted_entities"].update(entities)
            session["last_intent"] = intent_result.intent.value
        
        # Generate suggestions based on state
        if state == "gathering_meeting_info":
            missing = []
            if not entities.get("title"):
                missing.append("meeting title")
            if not entities.get("date"):
                missing.append("date")
            if not entities.get("time"):
                missing.append("time")
            if missing:
                suggestions = [f"Add {item}" for item in missing]
                
        elif state == "gathering_email_info":
            missing = []
            if not entities.get("recipient"):
                missing.append("recipient email")
            if not entities.get("body"):
                missing.append("message content")
            if missing:
                suggestions = [f"Add {item}" for item in missing]
        
        return ChatResponse(
            response=response_text,
            intent=intent_result.intent.value,
            entities=session["extracted_entities"],
            state=state,
            action_result=action_result,
            requires_confirmation=requires_confirmation,
            suggestions=suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/confirm-action")
async def confirm_action(confirmation: ActionConfirmation):
    """Confirm or cancel a pending action"""
    try:
        if confirmation.session_id not in session_states:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = session_states[confirmation.session_id]
        
        if not session.get("awaiting_confirmation"):
            return {"message": "No action pending confirmation"}
        
        if confirmation.confirmed:
            # Execute the action
            intent = session["last_intent"]
            entities = session["extracted_entities"]
            
            if intent == "schedule_meeting":
                result = executor.execute_meeting(entities)
            elif intent == "send_email":
                result = executor.execute_email(entities)
            else:
                result = {"status": "error", "message": "Unknown intent"}
            
            # Clear confirmation state
            session["awaiting_confirmation"] = False
            session["extracted_entities"] = {}
            
            return {
                "message": "Action executed successfully",
                "result": result
            }
        else:
            # Cancel the action
            session["awaiting_confirmation"] = False
            return {"message": "Action cancelled"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get session information"""
    if session_id not in session_states:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_states[session_id]
    return SessionInfo(
        session_id=session_id,
        created_at=session.get("created_at", ""),
        message_count=session.get("message_count", 0),
        last_intent=session.get("last_intent"),
        state="awaiting_confirmation" if session.get("awaiting_confirmation") else "idle"
    )

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a session"""
    if session_id in session_states:
        del session_states[session_id]
    return {"message": "Session cleared"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(session_states)
    }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            request = ChatRequest(message=data, session_id=session_id)
            response = await chat(request)
            await websocket.send_json(response.dict())
    except WebSocketDisconnect:
        print(f"Client {session_id} disconnected")


if __name__ == "__main__":
    # Port 7860 is required for Hugging Face Spaces
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=7860,
        log_level="info"
    )