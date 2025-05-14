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
from datetime import datetime
from .logger import system_logger

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
            
        system_logger.log("Initializing PersonalizedChatbot")
        
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
        
        system_logger.log("PersonalizedChatbot initialization complete")
        self._initialized = True

    def _validate_input(self, user_input: str) -> bool:
        """Validate user input before processing"""
        if not user_input or not isinstance(user_input, str):
            system_logger.log(f"Invalid input validation: {user_input}", "WARNING")
            return False
        if len(user_input) > 1000:  # Max length check
            system_logger.log(f"Input too long: {len(user_input)} characters", "WARNING")
            return False
        return True

    def get_response(self, user_input: str) -> str:
        system_logger.log(f"Processing user input: {user_input}")
        
        if not self._validate_input(user_input):
            return "Invalid input. Please try again."
        try:
            # Get current person from session
            current_person = self.session_manager.get_current_person()
            
            if not current_person:
                system_logger.log("No active person found in database", "ERROR")
                return "Error: No active person found in the database."
                
            system_logger.log(f"Current person: {current_person.id}")
                
            # Use the router to determine query type
            try:
                query_type = self.router.route_query(user_input)
                system_logger.log(f"Query type determined: {query_type}")
                
                # Handle attribute updates if needed
                attributes = {}
                if query_type == QueryType.ATTRIBUTES:
                    try:
                        system_logger.log("Processing attribute update")
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
                        system_logger.log(f"Attributes updated: {attributes}")
                    except Exception as e:
                        system_logger.log(f"Error updating attributes: {str(e)}", "ERROR")
                        attributes = {}
                
                # Get conversation history
                conversation_history = self.conversation_manager.format_conversation_history(current_person.id)
                system_logger.log("Retrieved conversation history")
                
                # Create personality-based prompt
                personality_prompt = self.personality_manager.create_personality_prompt(
                    current_person, 
                    conversation_history
                )
                system_logger.log("Created personality prompt")
                
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
                    system_logger.log(f"No agent found for query type: {query_type}", "ERROR")
                    return f"No agent found for query type: {query_type}"

                system_logger.log(f"Using agent for query type: {query_type}")

                # For LangGraph output (TODO, FILE)
                if query_type in [QueryType.TODO, QueryType.FILE]:
                    thread_id = f"user-{current_person.id}"
                    system_logger.log(f"Processing LangGraph request with thread_id: {thread_id}")
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
                        system_logger.log("No valid response generated from LangGraph", "WARNING")

                # Email agent: extract input string
                elif query_type == QueryType.EMAIL or query_type == QueryType.WHATSAPP or query_type == QueryType.VISION:
                    system_logger.log(f"Processing {query_type} request")
                    response = agent(input_data["input"])

                # LangChain agent: use .invoke()
                elif hasattr(agent, "invoke"):
                    system_logger.log("Processing LangChain agent request")
                    response = agent.invoke(input_data)

                # Function-style agent
                else:
                    system_logger.log("Processing function-style agent request")
                    response = agent(input_data)

                # Extract content if it's a LangChain message object
                if hasattr(response, "content"):
                    response = response.content

                # Update memory with the interaction
                self.memory_manager.update_memory(current_person.id, user_input, response)

                system_logger.log("Response generated successfully")
                return response

                
            except Exception as e:
                system_logger.log(f"Error processing request: {str(e)}", "ERROR")
                return "I had trouble processing your request. Please try again."
                
        except Exception as e:
            import traceback
            system_logger.log(f"Critical error: {str(e)}\n{traceback.format_exc()}", "CRITICAL")
            return "I apologize, but I'm having trouble at the moment. Please try again."

# Create a singleton instance
chatbot = PersonalizedChatbot() 
