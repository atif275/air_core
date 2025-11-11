"""Simplified Agent management module for the chatbot."""
from typing import Callable, Optional
from langchain_openai import ChatOpenAI
from .router import QueryType
from ..whatsapp_module.ai_agent_V5 import whatsapp_bot
from ..email_agent.email_chatbot import email_bot
from ..object_detection.object_detection import detect_objects
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from .todo_file_agents import todo_agent
from .logger import system_logger
import os
import sys
import requests

# No need for sys.path manipulation with proper imports

def file_agent_wrapper(input_data):
    """Wrapper for file agent that makes HTTP request to remote agent server"""
    try:
        # Make request to the remote agent server
        response = requests.post(
            "http://localhost:5003/api/agent/query",
            json={"query": input_data["input"]},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("response", "No response from file agent")
        else:
            return f"Error: File agent server returned status {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to file agent server. Make sure the remote agent server is running on port 5003."
    except Exception as e:
        return f"Error communicating with file agent: {str(e)}"

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
            QueryType.FILE: file_agent_wrapper,
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
