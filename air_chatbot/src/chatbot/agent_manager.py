"""Simplified Agent management module for the chatbot."""
from typing import Callable, Optional
from langchain_openai import ChatOpenAI
from .router import QueryType
from ..whatsapp_module.ai_agent_V5 import whatsapp_bot
from ..email_agent.email_chatbot import email_bot
from ..object_detection.object_detection import detect_objects
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from .todo_file_agents import todo_agent, file_agent
import logging
import os
import sys

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add the root directory to sys.path if not already there
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the spider_agent workflow
try:
    from spider_agent import app as spider_workflow
    logger.info("Successfully imported spider_agent workflow")
except ImportError as e:
    logger.error(f"Failed to import spider_agent: {e}")
    spider_workflow = None

class AgentManager:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.agents: dict[QueryType, Callable] = {
            QueryType.WHATSAPP: whatsapp_bot,
            QueryType.EMAIL: email_bot,
            QueryType.VISION: detect_objects,
            QueryType.TODO: todo_agent,
            QueryType.FILE: file_agent,
            QueryType.GENERAL: ChatPromptTemplate.from_messages([
                ("system", "{personality_prompt}"),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ]) | self.llm | RunnablePassthrough()
        }

    def get_agent(self, query_type: QueryType) -> Optional[Callable]:
        return self.agents.get(query_type)
