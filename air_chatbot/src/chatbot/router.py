"""Router module for the chatbot using LangGraph."""
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from collections import deque
import logging
import os
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create console handler with formatting
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Load environment variables
load_dotenv()

class QueryType(str, Enum):
    WHATSAPP = "whatsapp"
    TODO = "todo"
    FILE = "file"
    VISION = "vision"
    ATTRIBUTES = "attributes"
    EMAIL = "email"
    GENERAL = "general"

class QueryIntent(BaseModel):
    type: QueryType
    confidence: float
    context: Dict[str, Any] = Field(default_factory=dict)

class InteractionHistory:
    def __init__(self, max_size: int = 5):
        self.history = deque(maxlen=max_size)
        
    def add(self, query: str, response: str, query_type: Optional[QueryType] = None):
        """Add a new interaction to the history."""
        self.history.append((query, response, query_type))
        logger.info("\n" + "="*50)
        logger.info("CONVERSATION HISTORY:")
        logger.info("="*50)
        for i, (q, r, t) in enumerate(self.history, 1):
            type_str = f" (Type: {t.value})" if t else ""
            logger.info(f"\nInteraction {i}:")
            logger.info(f"  User: {q}")
            logger.info(f"  Assistant: {r}{type_str}")
            logger.info("-"*50)
        
    def get_formatted_history(self) -> str:
        """Format the history for the prompt."""
        if not self.history:
            return "No previous interactions."
            
        formatted = []
        for i, (query, response, query_type) in enumerate(self.history, 1):
            type_str = f" (Type: {query_type.value})" if query_type else ""
            formatted.append(f"Interaction {i}:")
            formatted.append(f"User: {query}")
            formatted.append(f"Assistant: {response}{type_str}")
            formatted.append("---")
            
        return "\n".join(formatted)

class RouterChain:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.last_query_type = None
        self.history = InteractionHistory(max_size=5)
        
        # Initialize LangGraph components
        self.checkpointer = InMemorySaver()
        self.store = InMemoryStore()
        
        # Create specialized agents for each query type
        self.agents = {}
        for query_type in QueryType:
            self.agents[query_type] = self._create_agent(query_type)
        
        # Create supervisor workflow
        self.workflow = self._create_workflow()
        
        # Compile the workflow
        self.app = self.workflow.compile(
            checkpointer=self.checkpointer,
            store=self.store
        )
    
    def _create_agent(self, query_type: QueryType):
        """Create a specialized agent for a query type."""
        prompt = f"""
        You are a specialized agent for handling {query_type.value} queries.
        Your task is to analyze the user's input and determine if it belongs to your domain.
        
        For {query_type.value} queries, look for:
        {self._get_query_type_indicators(query_type)}
        
        Respond with ONLY 'true' if the query belongs to your domain, 'false' otherwise.
        """
        
        return create_react_agent(
            model=self.llm,
            tools=[],  # No tools needed for routing
            name=f"{query_type.value}_router",
            prompt=prompt
        )
    
    def _get_query_type_indicators(self, query_type: QueryType) -> str:
        """Get indicators for each query type."""
        indicators = {
            QueryType.WHATSAPP: """
            - Checking for messages
            - Sending or replying to messages
            - Managing conversations
            - Following up on messages
            - Any communication intent
            """,
            QueryType.TODO: """
            - Creating reminders or tasks
            - Managing schedules
            - Tracking activities
            - Setting future actions
            - Viewing or checking task details
            """,
            QueryType.FILE: """
            - Managing digital content
            - Organizing information
            - Handling documents
            - Creating, reading, or modifying files
            """,
            QueryType.VISION: """
            - Understanding visual content
            - Analyzing images
            - Processing visual information
            - Any visual perception queries
            """,
            QueryType.ATTRIBUTES: """
            - Updating personal information
            - Modifying user attributes
            - Setting or changing user details
            - Providing personal context
            """,
            QueryType.EMAIL: """
            - Checking formal messages
            - Composing or sending formal communications
            - Managing email correspondence
            - Handling professional communications
            """,
            QueryType.GENERAL: """
            - Casual conversation
            - General information requests
            - Questions about knowledge
            - Basic assistance requests
            """
        }
        return indicators.get(query_type, "")
    
    def _create_workflow(self):
        """Create the supervisor workflow for routing."""
        return create_supervisor(
            list(self.agents.values()),
            model=self.llm,
            prompt="""
            You are a query router coordinator. Your task is to:
            1. Analyze the user's input
            2. Consider the conversation history
            3. Determine the most appropriate query type
            4. Return ONLY the type word (whatsapp, todo, file, vision, attributes, email, general)
            
            Previous Interactions:
            {history}
            
            Current query: {input}
            """
        )
    
    def route_query(self, query: str, response: str = "") -> QueryType:
        """Route a query using LangGraph workflow."""
        query = query.lower().strip()
        
        logger.info("\n" + "="*50)
        logger.info("PROCESSING NEW QUERY")
        logger.info("="*50)
        logger.info(f"Query: {query}")
        
        try:
            # Prepare input for the workflow
            input_data = {
                "messages": [{
                    "role": "user",
                    "content": query
                }],
                "history": self.history.get_formatted_history()
            }
            
            # Invoke the workflow
            result = self.app.invoke(
                input_data,
                {"configurable": {"thread_id": "router"}}
            )
            
            # Extract the response
            if result["messages"]:
                result = result["messages"][-1].content.strip().lower()
            else:
                result = QueryType.GENERAL.value
                
            # Log the raw response
            logger.info(f"Router raw response: {result}")
            
            # Determine the query type
            query_type = None
            if result in QueryType.__members__:
                query_type = QueryType(result)
            else:
                for q_type in QueryType:
                    if result == q_type.value.lower():
                        query_type = q_type
                        break
            
            # Default to general if no valid type found
            if not query_type:
                query_type = QueryType.GENERAL
            
            # Log the final type
            logger.info(f"Query type determined: {query_type.value}")
            logger.info("="*50 + "\n")
            
            # Update history
            self.history.add(query, response, query_type)
            self.last_query_type = query_type
            
            return query_type
            
        except Exception as e:
            logger.error(f"Error in routing: {str(e)}", exc_info=True)
            return QueryType.GENERAL