"""Query splitter module for handling multi-agent query splitting."""
import json
from typing import List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from .router import QueryType
from .logger import system_logger

class QuerySplitter:
    def __init__(self, llm: ChatOpenAI):
        """Initialize the query splitter with an LLM."""
        system_logger.log("Initializing QuerySplitter")
        self.llm = llm
        
        self.split_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a query splitter. Your task is to split a user's query into separate parts based on the required agent types.
            Each part should be a complete, self-contained query that can be handled by its respective agent.
            
            The available agent types are:
            - whatsapp: For instant messaging and communication
            - todo: For task management and reminders
            - file: For file operations and data management
            - vision: For visual analysis and image processing
            - attributes: For personal information management
            - email: For formal email communications
            - general: For general conversations and queries
            
            Rules:
            1. Split the query into exactly the number of parts as there are agent types
            2. Each part should be a complete, natural query
            3. Keep queries simple and direct
            4. First agent should get data, second agent should save/use that data
            5. Don't add unnecessary complexity or assumptions
            
            Examples:
            
            Example 1 (email -> file):
            Input: "Save all the pending mails in a file"
            Agent Types: [email, file]
            Output: [
                "List all pending emails",
                "Save the email list to a file"
            ]
            
            Example 2 (vision -> file):
            Input: "Save what you see in a file"
            Agent Types: [vision, file]
            Output: [
                "What do you see in front of you?",
                "Save the visual data to a file"
            ]
            
            Example 3 (todo -> file):
            Input: "Save my tasks to a file"
            Agent Types: [todo, file]
            Output: [
                "List all my tasks",
                "Save the task list to a file"
            ]
            
            Now, split this query into {num_parts} parts for the following agent types: {agent_types}
            
            Query: {query}
            
            Respond with ONLY a JSON array of strings, where each string is a complete query for its respective agent.
            The order of queries should match the order of agent types.
            Keep it simple and direct.
            """),
            ("human", "{query}")
        ])
        
        system_logger.log("QuerySplitter initialization complete")
    
    def split_query(self, query: str, query_types: List[QueryType]) -> List[Tuple[str, QueryType]]:
        """Split a multi-agent query into separate queries for each agent using LLM."""
        if len(query_types) == 1:
            return [(query, query_types[0])]
            
        try:
            # Create the chain with the available query_types
            split_chain = (
                {
                    "query": RunnablePassthrough(),
                    "num_parts": lambda _: len(query_types),
                    "agent_types": lambda _: [qt.value for qt in query_types]
                }
                | self.split_prompt
                | self.llm
                | RunnablePassthrough()
            )
            
            # Get the split queries
            result = split_chain.invoke(query)
            # Parse the JSON response
            split_queries = json.loads(result.content)
            
            # Validate the number of split queries matches the number of agent types
            if len(split_queries) != len(query_types):
                system_logger.log(f"Number of split queries ({len(split_queries)}) doesn't match number of agent types ({len(query_types)})", "WARNING")
                return [(query, query_types[0])]  # Fallback to original query
                
            # Pair each split query with its corresponding agent type
            return list(zip(split_queries, query_types))
            
        except Exception as e:
            system_logger.log(f"Error splitting query: {str(e)}", "ERROR")
            return [(query, query_types[0])]  # Fallback to original query