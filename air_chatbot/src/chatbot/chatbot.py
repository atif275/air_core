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
        self.personality_manager = PersonalityManager()
        self.conversation_manager = ConversationManager()
        self.session_manager = SessionManager()  # Initialize without memory manager
        self.memory_manager = MemoryManager(self.llm)
        
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
                    "personality_prompt": personality_prompt
                }
                
                if query_type == QueryType.ATTRIBUTES:
                    query_type = QueryType.GENERAL
                    
                agent = self.agent_manager.get_agent(query_type)
                if not agent:
                    logger.error(f"No agent found for query type: {query_type}")
                    return f"No agent found for query type: {query_type}"

                logger.info(f"Invoking {query_type} agent")

                # For LangGraph output (TODO, FILE)
                if query_type in [QueryType.TODO, QueryType.FILE]:
                    thread_id = f"user-{current_person.id}"
                    result = agent.invoke(
                        {"messages": [{"role": "user", "content": input_data["input"]}]},
                        {"configurable": {"thread_id": thread_id}}
                    )
                    
                    # Extract final AI message content
                    messages = result.get("messages", [])
                    if messages and hasattr(messages[-1], "content"):
                        response = messages[-1].content
                    else:
                        response = "No valid response generated."

                # Email agent: extract input string
                elif query_type == QueryType.EMAIL or query_type == QueryType.WHATSAPP or query_type == QueryType.VISION:
                    response = agent(input_data["input"])

                # LangChain agent: use .invoke()
                elif hasattr(agent, "invoke"):
                    response = agent.invoke(input_data)

                # Function-style agent
                else:
                    response = agent(input_data)

                # Extract content if it's a LangChain message object
                if hasattr(response, "content"):
                    response = response.content

                return response

                
            except Exception as e:
                logger.error(f"Error in query processing: {str(e)}")
                return "I had trouble processing your request. Please try again."
                
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "I apologize, but I'm having trouble at the moment. Please try again."

# Create a singleton instance
chatbot = PersonalizedChatbot() 
