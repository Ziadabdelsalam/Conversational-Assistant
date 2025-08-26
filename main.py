import gradio as gr
import json
from typing import List, Tuple, Dict
from agents.dialog_agent import DialogAgent
from executors.action_executor import ActionExecutor
from chains.confirmation_chain import ConfirmationChain
from chains.correction_chain import CorrectionChain
from config import Config
from models.schemas import ConversationContext, IntentType
from langchain.prompts import ChatPromptTemplate
import os
import uuid
# Add this import at the top
from helpers.date_context import DateContext
from datetime import datetime

# Update the process_message method to include date context
class ConversationalAssistant:
    def __init__(self):
        self.config = Config()
        if not self.config.OPENAI_API_KEY:
            raise ValueError("Please set OPENAI_API_KEY in .env file")
            
        self.dialog_agent = DialogAgent(self.config.OPENAI_API_KEY)
        self.executor = ActionExecutor(self.config.OUTBOX_PATH)
        self.confirmation_chain = ConfirmationChain(self.dialog_agent.llm)
        self.correction_chain = CorrectionChain(self.dialog_agent.llm)
        self.conversation_states = {}  # Store state per session
        
    def process_message(
        self, 
        message: str, 
        history: List[List[str]], 
        session_id: str
    ) -> Tuple[List[List[str]], str, str, str, dict]:
        """Process user message and return updated UI components"""
        
        if not message.strip():
            return history, "", "{}", "idle", {}
        
        # Add current date/time to message context
        date_context = DateContext.get_context_string()
        enhanced_message = f"[Context: {date_context}]\n\nUser message: {message}"
        
        # Get or create session state
        if session_id not in self.conversation_states:
            self.conversation_states[session_id] = {
                "context": ConversationContext(),
                "awaiting_confirmation": False,
                "extracted_entities": {},
                "last_intent": None
            }
        
        session_state = self.conversation_states[session_id]
        
        # Check for corrections
        if self.correction_chain.detect_correction(message) and session_state["extracted_entities"]:
            updated_entities = self.correction_chain.process_correction(
                message, 
                session_state["extracted_entities"]
            )
            session_state["extracted_entities"] = updated_entities
            
            # Generate new confirmation with updated details
            if session_state["last_intent"]:
                confirmation_msg = self.confirmation_chain.generate_confirmation(
                    session_state["last_intent"],
                    updated_entities
                )
                session_state["awaiting_confirmation"] = True
                response = confirmation_msg
            else:
                response = "I've updated the details. Please continue."
        
        # Check if we're waiting for confirmation
        elif session_state["awaiting_confirmation"]:
            response = self.handle_confirmation(message, session_state)
        else:
            # Process through dialog agent
            result = self.dialog_agent.graph.invoke({
                "messages": [message],
                "context": session_state["context"],
                "extracted_entities": session_state["extracted_entities"],
                "awaiting_confirmation": False,
                "current_intent": None,
                "missing_fields": [],
                "confirmation_message": "",
                "final_response": ""
            })
            
            # Update session state
            if result.get("current_intent"):
                session_state["context"].intent = result["current_intent"]
                session_state["last_intent"] = result["current_intent"]
            
            if result.get("extracted_entities"):
                session_state["extracted_entities"].update(result["extracted_entities"])
            
            # Check if we need confirmation
            if result.get("missing_fields"):
                response = result["final_response"]
            elif result["current_intent"] in [IntentType.SCHEDULE_MEETING, IntentType.SEND_EMAIL]:
                if not result.get("missing_fields"):
                    # All required fields present, ask for confirmation
                    confirmation_msg = self.confirmation_chain.generate_confirmation(
                        result["current_intent"],
                        session_state["extracted_entities"]
                    )
                    session_state["awaiting_confirmation"] = True
                    response = confirmation_msg
                else:
                    response = result["final_response"]
            else:
                response = result.get("final_response", "I'm here to help! You can ask me to schedule meetings or send emails.")
        
        # Update history
        history = history or []
        history.append([message, response])
        
        # Prepare display data
        intent_display = session_state["context"].intent.value if session_state["context"].intent else "None"
        entities_display = json.dumps(session_state["extracted_entities"], indent=2)
        state_display = "Awaiting Confirmation" if session_state["awaiting_confirmation"] else session_state["context"].state
        
        # Get last action if any
        recent_actions = self.executor.get_recent_actions(1)
        last_action = recent_actions[0] if recent_actions else {}
        
        return history, intent_display, entities_display, state_display, last_action
    
    def handle_confirmation(self, message: str, session_state: Dict) -> str:
        """Handle yes/no confirmation"""
        
        # Use LLM to understand if user confirmed or denied
        confirmation_check = ChatPromptTemplate.from_template("""
        Did the user confirm (yes) or deny (no) the action?
        User message: {message}
        
        Respond with only "YES", "NO", or "UNCLEAR".
        
        Examples of YES: yes, yeah, yep, sure, ok, confirm, go ahead, do it
        Examples of NO: no, nope, cancel, stop, don't, nevermind
        """)
        
        chain = confirmation_check | self.dialog_agent.llm
        result = chain.invoke({"message": message})
        
        decision = result.content.strip().upper()
        
        if decision == "YES":
            # Execute the action
            if session_state["context"].intent == IntentType.SCHEDULE_MEETING:
                result = self.executor.execute_meeting(session_state["extracted_entities"])
            elif session_state["context"].intent == IntentType.SEND_EMAIL:
                result = self.executor.execute_email(session_state["extracted_entities"])
            else:
                result = {"status": "error", "file": "unknown"}
            
            session_state["awaiting_confirmation"] = False
            session_state["context"].state = "completed"
            
            # Clear entities for next action
            session_state["extracted_entities"] = {}
            session_state["last_intent"] = None
            
            action_type = session_state["context"].intent.value.replace('_', ' ')
            return f"✅ Done! I've successfully {action_type}. The details have been saved to {result['file']}. Is there anything else I can help you with?"
            
        elif decision == "NO":
            session_state["awaiting_confirmation"] = False
            session_state["context"].state = "idle"
            return "No problem! I've cancelled that action. Is there anything else you'd like me to help with?"
        
        else:
            return "I didn't quite catch that. Could you please say 'yes' to confirm or 'no' to cancel?"
    
    def clear_session(self, session_id: str):
        """Clear session state"""
        if session_id in self.conversation_states:
            del self.conversation_states[session_id]
    
    def create_interface(self):
        """Create Gradio interface"""
        
        with gr.Blocks(theme=gr.themes.Soft(), title="AI Assistant") as demo:
            session_id = gr.State(value=lambda: str(uuid.uuid4()))
            
            gr.Markdown(
                """
                # Conversational Assistant
                
                I can help you:
                - 📅 **Schedule meetings** - Just tell me when and with whom
                - ✉️ **Send emails** - Tell me the recipient and message
                - 💬 **Chat** - I'm here for general conversation too!
                
                Try saying things like:
                - "Book a meeting with Sara tomorrow at 3pm"
                - "Send an email to john@example.com about the project update"
                """
            )
            
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(
                        height=500,
                        bubble_full_width=False,
                        avatar_images=(None, "🤖"),
                        elem_id="chatbot"
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder="Try: 'Book a meeting with Sara tomorrow at 3pm' or 'Send an email to john@example.com'",
                            label="Your Message",
                            scale=9,
                            lines=1
                        )
                        send_btn = gr.Button("Send", scale=1, variant="primary")
                    
                    with gr.Row():
                        clear_btn = gr.Button("🗑️ Clear Chat", scale=1)
                        
                with gr.Column(scale=1):
                    gr.Markdown("### 📊 Current Context")
                    
                    with gr.Group():
                        intent_display = gr.Textbox(
                            label="Detected Intent",
                            interactive=False,
                            value="None",
                            lines=1
                        )
                        
                        state_display = gr.Textbox(
                            label="Conversation State",
                            interactive=False,
                            value="idle",
                            lines=1
                        )
                    
                    entities_display = gr.Code(
                        label="Extracted Information",
                        language="json",
                        interactive=False,
                        value="{}",
                        lines=8
                    )
                    
                    gr.Markdown("### 📁 Last Action")
                    actions_display = gr.JSON(
                        label="Most Recent Action",
                        value={},
                        elem_id="actions"
                    )
            
            # Event handlers
            def respond(message, history, session):
                if not message.strip():
                    return history, "", "{}", "idle", {}
                    
                try:
                    hist, intent, entities, state, action = self.process_message(message, history, session)
                    return hist, intent, entities, state, action
                except Exception as e:
                    print(f"Error processing message: {e}")
                    history = history or []
                    history.append([message, f"I encountered an error: {str(e)}. Please try again."])
                    return history, "error", "{}", "error", {}
            
            def clear_chat(session):
                self.clear_session(session)
                return [], "None", "{}", "idle", {}, str(uuid.uuid4())
            
            msg.submit(
                respond,
                [msg, chatbot, session_id],
                [chatbot, intent_display, entities_display, state_display, actions_display],
                queue=False
            ).then(
                lambda: "",
                None,
                msg,
                queue=False
            )
            
            send_btn.click(
                respond,
                [msg, chatbot, session_id],
                [chatbot, intent_display, entities_display, state_display, actions_display],
                queue=False
            ).then(
                lambda: "",
                None,
                msg,
                queue=False
            )
            
            clear_btn.click(
                clear_chat,
                [session_id],
                [chatbot, intent_display, entities_display, state_display, actions_display, session_id],
                queue=False
            )
            
            # Examples
            gr.Examples(
                examples=[
                    "Book a meeting with Sara tomorrow at 3pm about project sync",
                    "Send an email to alice@example.com saying I'll be late to the meeting",
                    "Schedule a call with the team next Monday at 10am",
                    "Write an email to bob@company.com about the quarterly report",
                    "Actually, make that 4pm instead",
                    "Hello! How are you today?"
                ],
                inputs=msg
            )
        
        return demo

if __name__ == "__main__":
    try:
        app = ConversationalAssistant()
        demo = app.create_interface()
        print("Starting Gradio app on http://localhost:7860")
        demo.launch(
            share=False, 
            server_name="0.0.0.0", 
            server_port=7860,
            show_error=True
        )
    except Exception as e:
        print(f"Error starting application: {e}")
        print("Please make sure you have set OPENAI_API_KEY in your .env file")