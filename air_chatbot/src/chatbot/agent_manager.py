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
from .logger import system_logger
import os
import sys

# Add the root directory to sys.path if not already there
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

class AgentManager:
    def __init__(self, llm: ChatOpenAI):
        system_logger.log("Initializing AgentManager")
        self.llm = llm
        system_logger.log("Setting up agent mappings")
        
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
        system_logger.log(f"Agent mappings initialized with {len(self.agents)} agents")

    def get_agent(self, query_type: QueryType) -> Optional[Callable]:
        system_logger.log(f"Getting agent for query type: {query_type.value}")
        agent = self.agents.get(query_type)
        if agent:
            system_logger.log(f"Found agent for {query_type.value}")
        else:
            system_logger.log(f"No agent found for {query_type.value}", "WARNING")
        return agent
