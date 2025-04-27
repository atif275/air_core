"""Agent management module for the chatbot."""
from typing import Any, Dict, Optional
import logging
import os
import sys
import uuid
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from .router import QueryType
from ..object_detection.object_detection import detect_objects
from ..whatsapp_module.ai_agent_V5 import whatsapp_bot
from ..email_agent.email_chatbot import email_bot
from ..attributes_management.attributes_management import (
    identify_attributes,
    update_person_attributes,
    determine_age_group,
    get_casual_expressions
)

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add the root directory to sys.path if not already there
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the spider_agent workflow (this will be imported from the root directory)
try:
    from spider_agent import app as spider_workflow, context as spider_context
    logger.info("Successfully imported spider_agent workflow")
except ImportError as e:
    logger.error(f"Failed to import spider_agent: {e}")
    spider_workflow = None
    spider_context = None

class AgentWrapper:
    """Wrapper to standardize agent interfaces."""
    
    def __init__(self, agent: Any, agent_type: QueryType, agent_manager: 'AgentManager' = None):
        self.agent = agent
        self.agent_type = agent_type
        self.thread_id = str(uuid.uuid4())  # For spider_agent persistence
        self.agent_manager = agent_manager  # Store reference to AgentManager
        
    def _prepare_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare standardized input for all agent types."""
        base_input = {
            "input": input_data.get("input", ""),
            "chat_history": input_data.get("chat_history", []),
            "context": input_data.get("context", {})
        }
        
        # Add type-specific context
        if self.agent_type == QueryType.VISION:
            base_input["context"]["vision_guidelines"] = "Analyze images thoroughly and provide detailed observations."
            # Transform input to match detect_objects signature
            base_input["user_question"] = base_input["input"]
        elif self.agent_type == QueryType.WHATSAPP:
            # Enhanced WhatsApp context
            base_input["context"].update({
                "message_format": "whatsapp",
                "person_name": input_data.get("context", {}).get("person_name", ""),
                "person_age": input_data.get("context", {}).get("person_age", ""),
                "is_vision_query": input_data.get("context", {}).get("is_vision_query", False),
                "personality_prompt": input_data.get("context", {}).get("personality_prompt", ""),
                "conversation_history": input_data.get("chat_history", [])
            })
            logger.info("Prepared WhatsApp context with enhanced information")
        elif self.agent_type == QueryType.GENERAL:
            # Extract personality prompt from context for general agent
            base_input["personality_prompt"] = base_input["context"].get("personality_prompt", "")
        elif self.agent_type == QueryType.FILE:
            # For file operations, use the original input if available in context
            if "original_input" in input_data.get("context", {}):
                base_input["input"] = input_data["context"]["original_input"]
        
        return base_input
        
    def _format_output(self, result: Any) -> str:
        """Standardize output format across all agent types."""
        if result is None:
            return "No response generated."
            
        if isinstance(result, str):
            return result
            
        if hasattr(result, "content"):
            return result.content
            
        if isinstance(result, dict):
            return result.get("output", str(result))
            
        return str(result)
        
    def invoke(self, input_data: Dict[str, Any]) -> str:
        """
        Standardized invocation method for all agent types.
        
        Args:
            input_data: Dictionary containing:
                - input: str, the user's input
                - chat_history: Optional[List], conversation history
                - context: Optional[Dict], additional context
        
        Returns:
            str: The agent's response
        """
        try:
            # Special case for FILE and TODO types - use spider_agent
            if (self.agent_type == QueryType.FILE or self.agent_type == QueryType.TODO) and spider_workflow:
                logger.info(f"Delegating {self.agent_type} request to spider_agent: {input_data['input']}")
                
                user_input = input_data["input"]
                
                # Pre-process user input to handle file references
                referenced_file = spider_context.get_referenced_file(user_input)
                if referenced_file:
                    logger.info(f"Referenced file: {referenced_file}")
                    # Replace vague references with the specific path
                    if "this file" in user_input.lower():
                        modified_input = user_input.lower().replace("this file", f"the file at '{referenced_file}'")
                        logger.info(f"Modified input: {modified_input}")
                        user_input = modified_input
                    elif "the file" in user_input.lower() and os.path.basename(referenced_file) not in user_input:
                        modified_input = user_input.lower().replace("the file", f"the file at '{referenced_file}'")
                        logger.info(f"Modified input: {modified_input}")
                        user_input = modified_input
                
                # Invoke the spider_agent workflow
                result = spider_workflow.invoke(
                    {"messages": [{"role": "user", "content": user_input}]},
                    {"configurable": {"thread_id": self.thread_id}}
                )
                
                # Extract the final response
                if result["messages"]:
                    final_response = result["messages"][-1].content
                    
                    # Update context if this was a find_files result
                    if "Found" in final_response and "file(s)" in final_response:
                        spider_context.update_found_files(final_response)
                    
                    return final_response
                else:
                    return "I couldn't process that file or task operation."
            
            # Special case for attributes which uses pre-computed response
            elif self.agent_type == QueryType.ATTRIBUTES:
                # Get the attributes response
                attr_response = input_data.get("context", {}).get("attr_response", 
                    "Could not process attribute update.")
                
                # Get the general agent through the agent manager
                if self.agent_manager:
                    general_agent = self.agent_manager.get_agent(QueryType.GENERAL)
                    if general_agent:
                        # Prepare input for general agent
                        general_input = {
                            "input": input_data["input"],
                            "chat_history": input_data.get("chat_history", []),
                            "context": input_data.get("context", {})
                        }
                        # Get general agent response
                        general_response = general_agent.invoke(general_input)
                        
                        # Combine responses
                        return f"{attr_response}\n\n{general_response}"
                
                return attr_response

            # Prepare standardized input for other agent types
            prepared_input = self._prepare_input(input_data)
            
            # Invoke agent based on its type
            if hasattr(self.agent, "invoke"):
                # LangChain agents (VISION, ATTRIBUTES, GENERAL)
                result = self.agent.invoke(prepared_input)
            elif callable(self.agent):
                # Function-based agents (VISION, WHATSAPP)
                if self.agent_type == QueryType.WHATSAPP:
                    try:
                        logger.info("Invoking WhatsApp agent with prepared input")
                        result = self.agent(
                            user_query=prepared_input["input"],
                            **prepared_input["context"]
                        )
                        logger.info("WhatsApp agent response received")
                    except Exception as e:
                        logger.error(f"Error in WhatsApp agent invocation: {str(e)}")
                        return f"I encountered an error while processing your WhatsApp request: {str(e)}. Please try again."
                elif self.agent_type == QueryType.VISION:
                    # Use the properly transformed input for vision queries
                    result = self.agent(user_question=prepared_input["user_question"])
                else:
                    result = self.agent(prepared_input["input"])
            else:
                raise ValueError(f"Unsupported agent type: {self.agent_type}")

            # Format output consistently
            return self._format_output(result)
                
        except Exception as e:
            from .error_handler import ErrorHandler
            logger.error(f"Error in agent invocation: {str(e)}", exc_info=True)
            return ErrorHandler.handle_error(
                error=e,
                context=f"agent_invocation_{self.agent_type}",
                fallback_value="I had trouble processing that request. Please try again."
            )

class AgentManager:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.agents = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize specialized agents for each query type"""
        # WhatsApp Agent - using our modified ai_agent_V5 module
        self.agents[QueryType.WHATSAPP] = AgentWrapper(
            whatsapp_bot,
            QueryType.WHATSAPP,
            self  # Pass self (AgentManager) to AgentWrapper
        )
        
        # Email Agent - using our email_chatbot module
        self.agents[QueryType.EMAIL] = AgentWrapper(
            email_bot,
            QueryType.EMAIL,
            self  # Pass self (AgentManager) to AgentWrapper
        )
        
        # Vision Agent
        self.agents[QueryType.VISION] = AgentWrapper(
            detect_objects,
            QueryType.VISION,
            self  # Pass self (AgentManager) to AgentWrapper
        )
        
        # Attributes Agent
        self.agents[QueryType.ATTRIBUTES] = AgentWrapper(
            initialize_agent(
                tools=[
                    identify_attributes,
                    update_person_attributes,
                    determine_age_group,
                    get_casual_expressions
                ],
                llm=self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3,
                early_stopping_method="generate"
            ),
            QueryType.ATTRIBUTES,
            self  # Pass self (AgentManager) to AgentWrapper
        )
        
        # Todo Agent - using spider_agent
        self.agents[QueryType.TODO] = AgentWrapper(
            spider_workflow,  # The spider_agent workflow handles todo operations
            QueryType.TODO,
            self  # Pass self (AgentManager) to AgentWrapper
        )
        
        # File Agent - using spider_agent
        self.agents[QueryType.FILE] = AgentWrapper(
            spider_workflow,  # The spider_agent workflow handles file operations
            QueryType.FILE,
            self  # Pass self (AgentManager) to AgentWrapper
        )
        
        # General Conversation Agent
        self.agents[QueryType.GENERAL] = AgentWrapper(
            ChatPromptTemplate.from_messages([
                ("system", "{personality_prompt}"),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ]) | self.llm | RunnablePassthrough(),
            QueryType.GENERAL,
            self  # Pass self (AgentManager) to AgentWrapper
        )

    def get_agent(self, query_type: QueryType) -> Optional[AgentWrapper]:
        """Get the appropriate agent for the query type"""
        return self.agents.get(query_type) 