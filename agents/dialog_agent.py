from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from state.conversation_state import ConversationState
from models.schemas import ConversationContext, IntentType, MeetingDetails, EmailDetails
from agents.intent_classifier import IntentClassifierAgent
from agents.entity_extractor import EntityExtractorAgent
from typing import Dict, Literal

class DialogAgent:
    def __init__(self, api_key: str):
        self.llm = ChatOpenAI(api_key=api_key, model_name="gpt-4o-mini", temperature=0.3)
        self.intent_classifier = IntentClassifierAgent(api_key)
        self.entity_extractor = EntityExtractorAgent(api_key)
        self.graph = self.build_graph()
        
    def build_graph(self):
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("classify_intent", self.classify_intent_node)
        workflow.add_node("extract_entities", self.extract_entities_node)
        workflow.add_node("check_completeness", self.check_completeness_node)
        workflow.add_node("ask_missing_info", self.ask_missing_info_node)
        workflow.add_node("generate_confirmation", self.generate_confirmation_node)
        workflow.add_node("process_confirmation", self.process_confirmation_node)
        workflow.add_node("execute_action", self.execute_action_node)
        workflow.add_node("handle_chitchat", self.handle_chitchat_node)
        
        # Define edges
        workflow.set_entry_point("classify_intent")
        
        workflow.add_conditional_edges(
            "classify_intent",
            self.route_by_intent,
            {
                "extract": "extract_entities",
                "chitchat": "handle_chitchat"
            }
        )
        
        workflow.add_edge("extract_entities", "check_completeness")
        
        workflow.add_conditional_edges(
            "check_completeness",
            self.route_by_completeness,
            {
                "incomplete": "ask_missing_info",
                "complete": "generate_confirmation"
            }
        )
        
        workflow.add_edge("ask_missing_info", END)
        workflow.add_edge("generate_confirmation", END)
        workflow.add_edge("process_confirmation", "execute_action")
        workflow.add_edge("execute_action", END)
        workflow.add_edge("handle_chitchat", END)
        
        return workflow.compile()
    
    def route_by_intent(self, state: ConversationState) -> Literal["extract", "chitchat"]:
        """Route based on intent"""
        if state["current_intent"] in [IntentType.SCHEDULE_MEETING, IntentType.SEND_EMAIL]:
            return "extract"
        return "chitchat"
    
    def route_by_completeness(self, state: ConversationState) -> Literal["incomplete", "complete"]:
        """Route based on whether all required fields are present"""
        if state["missing_fields"]:
            return "incomplete"
        return "complete"
    
    def classify_intent_node(self, state: ConversationState):
        """Classify user intent"""
        latest_message = state["messages"][-1] if state["messages"] else ""
        classification = self.intent_classifier.classify(latest_message)
        
        return {
            "current_intent": classification.intent,
            "context": ConversationContext(
                intent=classification.intent,
                raw_user_input=latest_message
            )
        }
    
    def extract_entities_node(self, state: ConversationState):
        """Extract entities based on intent"""
        intent = state["current_intent"]
        message = state["messages"][-1]
        
        if intent == IntentType.SCHEDULE_MEETING:
            entities = self.entity_extractor.extract_meeting_entities(
                message, 
                state.get("extracted_entities", {})
            )
            return {"extracted_entities": entities.dict()}
            
        elif intent == IntentType.SEND_EMAIL:
            entities = self.entity_extractor.extract_email_entities(
                message,
                state.get("extracted_entities", {})
            )
            return {"extracted_entities": entities.dict()}
        
        return {}
    
    def check_completeness_node(self, state: ConversationState):
        """Check if all required fields are present"""
        intent = state["current_intent"]
        entities = state["extracted_entities"]
        
        required_fields = {
            IntentType.SCHEDULE_MEETING: ["title", "date", "time"],
            IntentType.SEND_EMAIL: ["recipient", "body"]
        }
        
        missing = []
        for field in required_fields.get(intent, []):
            if not entities.get(field):
                missing.append(field)
        
        return {"missing_fields": missing}
    
    def ask_missing_info_node(self, state: ConversationState):
        """Generate questions for missing information"""
        missing = state["missing_fields"]
        
        prompt = ChatPromptTemplate.from_template("""
        The user wants to {intent} but we're missing: {missing_fields}.
        Generate a natural, friendly question to ask for the missing information.
        Ask for only the first missing field in a conversational way.
        
        Missing field: {first_missing}
        
        Be specific and helpful. For example:
        - For 'title': "What would you like to call this meeting?"
        - For 'date': "What day would you like to schedule this?"
        - For 'time': "What time works best for you?"
        - For 'recipient': "Who should I send this email to?"
        - For 'body': "What would you like to say in the email?"
        """)
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "intent": state["current_intent"].value.replace("_", " "),
            "missing_fields": ", ".join(missing),
            "first_missing": missing[0] if missing else ""
        })
        
        return {"final_response": response.content}
    
    def generate_confirmation_node(self, state: ConversationState):
        """Generate confirmation message"""
        intent = state["current_intent"]
        entities = state["extracted_entities"]
        
        if intent == IntentType.SCHEDULE_MEETING:
            confirmation = f"Should I book a meeting '{entities.get('title', 'Meeting')}' on {entities.get('date')} at {entities.get('time')}?"
        elif intent == IntentType.SEND_EMAIL:
            confirmation = f"Should I send an email to {entities.get('recipient')} saying: '{entities.get('body')}'?"
        else:
            confirmation = "Should I proceed with this action?"
        
        return {
            "confirmation_message": confirmation,
            "awaiting_confirmation": True,
            "final_response": confirmation
        }
    
    def process_confirmation_node(self, state: ConversationState):
        """Process user's confirmation response"""
        # This is handled in the main app
        return {}
    
    def execute_action_node(self, state: ConversationState):
        """Execute the confirmed action"""
        # This is handled in the main app
        return {"final_response": "Action executed successfully!"}
    
    def handle_chitchat_node(self, state: ConversationState):
        """Handle general conversation"""
        prompt = ChatPromptTemplate.from_template("""
        Respond to this general conversation in a friendly, helpful way.
        Keep your response brief and natural.
        
        User: {message}
        """)
        
        chain = prompt | self.llm
        
        response = chain.invoke({
            "message": state["messages"][-1] if state["messages"] else "Hello"
        })
        
        return {"final_response": response.content}