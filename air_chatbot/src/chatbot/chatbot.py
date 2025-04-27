"""Chatbot module for handling user interactions."""
import os
from typing import Dict, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from ..attributes_management.attributes_management import (
    identify_attributes,
    update_person_attributes
)
from .router import QueryType, RouterChain
from .agent_manager import AgentManager
from .memory_manager import MemoryManager
from .vision_manager import VisionManager
from .response_manager import ResponseManager
from .personality_manager import PersonalityManager
from .session_manager import SessionManager
from .conversation_manager import ConversationManager
import logging
from datetime import datetime

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

class PersonalizedChatbot:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PersonalizedChatbot, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the chatbot with LangChain components and database connection."""
        if self._initialized:
            return
            
        self.llm = ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0.9,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize managers in correct order
        self.router = RouterChain(self.llm)
        self.agent_manager = AgentManager(self.llm)
        self.vision_manager = VisionManager(self.llm)
        self.personality_manager = PersonalityManager()
        self.conversation_manager = ConversationManager()
        self.session_manager = SessionManager()  # Initialize without memory manager
        self.memory_manager = MemoryManager(self.llm)
        self.response_manager = ResponseManager(self.memory_manager, self.router)
        
        # Set up bidirectional references
        self.session_manager.set_memory_manager(self.memory_manager)  # Set memory manager in session manager
        self.memory_manager.set_session_manager(self.session_manager)  # Set session manager in memory manager
        
        self._initialized = True

    def _validate_input(self, user_input: str) -> bool:
        """Validate user input before processing"""
        if not user_input or not isinstance(user_input, str):
            return False
        if len(user_input) > 1000:  # Max length check
            return False
        # Add more validation rules
        return True

    def get_response(self, user_input: str) -> str:
        if not self._validate_input(user_input):
            return "Invalid input. Please try again."
        try:
            # Get current person from session
            current_person = self.session_manager.get_current_person()
            
            if not current_person:
                return "Error: No active person found in the database."
                
            # Use the router to determine query type
            try:
                query_type = self.router.route_query(user_input)
                logger.info(f"Query type determined: {query_type}")
                
                # Handle attribute updates if needed
                attributes = {}
                attributes_updated = False
                if query_type == QueryType.ATTRIBUTES:
                    try:
                        # Use the imported identify_attributes function
                        attributes = identify_attributes.invoke({
                            "input": {"user_input": user_input}
                        })
                        # Use the imported update_person_attributes function
                        attributes_updated = update_person_attributes.invoke({
                            "input": {
                                "person_id": current_person.id,
                                "attributes": attributes
                            }
                        })
                    except Exception as e:
                        logger.error(f"Error processing attributes: {str(e)}")
                        attributes = {}
                        attributes_updated = False
                
                # Check if this is a vision query
                is_vision_query = self.vision_manager.is_vision_query(user_input)
                
                # Get conversation history
                conversation_history = self.conversation_manager.format_conversation_history(current_person.id)
                
                # Create personality-based prompt
                personality_prompt = self.personality_manager.create_personality_prompt(
                    current_person, 
                    conversation_history
                )
                
                # Prepare input data with context
                input_data = {
                    "input": user_input,
                    "chat_history": self.memory_manager.get_memory(current_person.id).chat_memory.messages if current_person.id in self.memory_manager.get_memory_ids() else [],
                    "context": {
                        "person_name": current_person.name,
                        "person_age": current_person.age,
                        "is_vision_query": is_vision_query,
                        "personality_prompt": personality_prompt,
                        "attr_response": "", # Response manager will handle attribute updates
                        # Add WhatsApp specific context
                        "whatsapp_context": {
                            "person_id": current_person.id,
                            "person_name": current_person.name,
                            "conversation_history": conversation_history,
                            "memory": self.memory_manager.get_memory(current_person.id).chat_memory.messages if current_person.id in self.memory_manager.get_memory_ids() else []
                        }
                    }
                }

                # Get response from the appropriate agent
                agent = self.agent_manager.get_agent(query_type)
                if not agent:
                    logger.error(f"No agent found for query type: {query_type}")
                    return f"No agent found for query type: {query_type}"
                
                logger.info(f"Invoking {query_type} agent")
                response = agent.invoke(input_data)
                logger.info(f"Received response from {query_type} agent")

                # Process the final response using the response manager
                return self.response_manager.process_response(
                    response=response,
                    user_input=user_input,
                    person_id=current_person.id,
                    age=current_person.age,
                    should_update_attributes=attributes_updated,
                    attributes=attributes
                )
                
            except Exception as e:
                logger.error(f"Error in query processing: {str(e)}")
                return "I had trouble processing your request. Please try again."
                
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "I apologize, but I'm having trouble at the moment. Please try again."

    def get_conversation_history(self, person_id: Optional[int] = None) -> Dict:
        """Get conversation history for a person."""
        if person_id is None:
            current_person = self.session_manager.get_current_person()
            if current_person:
                person_id = current_person.id
        return self.conversation_manager.get_conversation_history(person_id)

    def get_active_user_id(self) -> Optional[int]:
        """Get the ID of the currently active user."""
        return self.session_manager.get_active_user_id()

    def switch_active_person(self, person_id: int) -> bool:
        """
        Switch the active person to the specified person ID.
        Returns True if successful, False otherwise.
        """
        try:
            # Store old person's ID before switching
            old_person_id = self.session_manager.get_current_person().id if self.session_manager.get_current_person() else None
            
            # Clear any existing active records
            self.session_manager.clear_active_person()
            
            # Set new active person
            self.session_manager.switch_active_person(person_id)
            
            # Always reinitialize memory for the new person to ensure fresh context
            if person_id in self.memory_manager.get_memory_ids():
                # Clear existing memory to force fresh context
                self.memory_manager.clear_memory(person_id)
            
            # Initialize fresh memory with current context
            self.memory_manager.initialize_memory(person_id)
            
            # Update last used timestamp for the new person only
            self.memory_manager.update_last_used(person_id)
            
            # Update last active check time
            self.session_manager.update_last_active_check()
            
            # DO NOT update old person's last_used timestamp
            # This will allow it to become inactive after 1 minute
            
            return True
        except Exception as e:
            print(f"Error switching active person: {str(e)}")
            return False

# Create a singleton instance
chatbot = PersonalizedChatbot() 