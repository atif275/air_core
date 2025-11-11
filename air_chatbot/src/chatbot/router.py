"""Router module for the chatbot."""
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from collections import deque
from .logger import system_logger

class QueryType(str, Enum):
    WHATSAPP = "whatsapp"
    TODO = "todo"
    FILE = "file"
    VISION = "vision"
    ATTRIBUTES = "attributes"
    EMAIL = "email"
    GENERAL = "general"

class InteractionHistory:
    def __init__(self, max_size: int = 1):
        self.history = deque(maxlen=max_size)
        
    def add(self, query: str, response: str, query_types: List[QueryType] = None):
        """Add a new interaction to the history."""
        self.history.append((query, response, query_types))
        
    def get_formatted_history(self) -> str:
        """Format the history for the prompt."""
        if not self.history:
            return "No previous interactions."
            
        formatted = []
        for i, (query, response, query_types) in enumerate(self.history, 1):
            type_str = f" (Types: {', '.join(qt.value for qt in query_types)})" if query_types else ""
            formatted.append(f"Interaction {i}:")
            formatted.append(f"User: {query}")
            formatted.append(f"Assistant: {response}{type_str}")
            formatted.append("---")
            
        return "\n".join(formatted)

class RouterChain:
    def __init__(self, llm: ChatOpenAI):
        system_logger.log("Initializing RouterChain")
        self.llm = llm
        self.history = InteractionHistory(max_size=1)  # Track last 1 interaction[s]
        
        self.router_prompt = ChatPromptTemplate.from_messages([
            ("system", """
                IMPORTANT: You must respond with ONLY the type words (one or more of: whatsapp, todo, file, vision, attributes, email, general) separated by commas and NOTHING else. Do not include explanations, markdown, or any other text. Your response must be exactly one or more of these words, in lowercase, with no punctuation except commas between types.

                You are an intelligent query router. Your job is to analyze user queries and determine ALL appropriate types that need to be executed in sequence.
                The possible types are (RESPOND WITH ONE OR MORE OF THESE LOWERCASE WORDS, SEPARATED BY COMMAS):

                - whatsapp: For communication intents through instant messaging, including:
                * Intent to check messages or message status
                * Intent to communicate with contacts
                * Intent to send or reply to messages
                * Intent to manage conversations
                * Intent to follow up on previous messages
                * Any communication intent that's immediate/instant in nature
                * ANY request to check for messages from someone
                * ANY query about message status or presence
                * ANY request to check for messages in general
                * Examples:
                    - "tell me if i have any message from usama"
                    - "do i have any messages from john"
                    - "check if there are messages from mary"
                    - "are there any messages from david"
                    - "show me messages from lisa"
                    - "any messages from tom"
                    - "what messages do i have from sarah"
                    - "check messages from mike"
                    - "do i have any messages"
                    - "check my messages"
                    - "any new messages"
                    - "show me my messages"
                    - "what messages do i have"
                    - "are there any messages"
                * Use 'whatsapp' for ANY message checking request
                * Use 'whatsapp' for ANY message status query
                * Use 'whatsapp' for ANY general message check
                * The key is checking for or about messages

                - email: For formal communication intents, including:
                * Intent to check formal messages
                * Intent to compose or send formal communications
                * Intent to manage email correspondence
                * Intent to handle professional communications
                * Intent to follow up on email threads
                * Any communication intent that's formal/professional in nature
                * ANY request to reply to or respond to emails
                * ANY request to compose or send emails
                * ANY request to manage email correspondence
                * Examples:
                    - "reply to that email"
                    - "respond to his message"
                    - "send him an email"
                    - "write back to them"
                    - "reply to him accordingly"
                    - "respond to that"
                    - "answer that email"
                    - "send a response"

                - todo: For task management intents, including:
                * Intent to create reminders or tasks
                * Intent to manage schedules
                * Intent to track activities
                * Intent to set future actions
                * Intent to view or check task details
                * Intent to update task status
                * Intent to modify task properties
                * Any intent related to future task planning
                * ANY request that starts with "remind me to" or "remember to"
                * ANY request that involves future actions or scheduling
                * ANY request that involves task creation or management
                * ANY request to view or check task details
                * ANY request to update task status or properties
                * Examples:
                    - "remind me to call John tomorrow"
                    - "remember to buy groceries"
                    - "set a reminder to email the report"
                    - "create a task to meet with the team"
                    - "schedule a meeting for next week"
                    - "add a reminder to check the mail"
                    - "set a task to review the document"
                    - "remind me to mail sabhee tomorrow"
                    - "show me my tasks"
                    - "what tasks do I have"
                    - "show task details"
                    - "mark task as done"
                    - "update task priority"
                    - "check my tasks"
                    - "view task details"
                    - "display task information"
                    - "show the task again"
                    - "show task details again"
                    - "mark it done"
                    - "mark task completed"
                    - "why isn't it marked completed"
                * These are ALL todo tasks, even if they involve viewing or updating
                * The key is the task management aspect

                - file: For data management intents, including:
                * Intent to manage digital content
                * Intent to organize information
                * Intent to handle documents
                * Intent to create, read, or modify files
                * Intent to save information to files
                * Any intent related to digital asset management
                * When combined with other operations (e.g., "save X to file Y")
                * ONLY use for actual file operations
                * DO NOT use for general questions or requests
                * DO NOT use for number spelling or general information
                * DO NOT use just because previous interactions were about files
                * Examples:
                    - "create a file called notes.txt"
                    - "read the content of document.txt"
                    - "save this to a file"
                    - "rename the file to newname.txt"

                - vision: For visual analysis intents, including:
                * Intent to understand visual content
                * Intent to analyze images
                * Intent to process visual information
                * Any intent related to visual data
                * ANY request about visual perception or sight
                * ANY question about what is seen or visible
                * ANY query about visual observation
                * ANY question about what you see
                * ANY request to describe what you see
                * ANY query about your visual perception
                * Examples:
                    - "What do you see in front of you?"
                    - "What's in this image?"
                    - "Describe what you see"
                    - "Can you see anything?"
                    - "What's visible in the picture?"
                    - "Tell me what you observe"
                    - "What's in your view?"
                    - "What can you see?"
                    - "What do you see?"
                    - "Describe your view"
                    - "What's visible to you?"
                    - "What's in your field of vision?"
                * Use 'vision' for ANY query about visual perception, even if metaphorical
                * Use 'vision' for questions about sight or observation
                * Use 'vision' for requests to describe visual content
                * Use 'vision' for ANY question about what you see
                * The key is the visual perception aspect

                - attributes: For personal information and attributes, including:
                * Intent to update or share personal information
                * Intent to modify user attributes
                * Intent to set or change user details
                * Intent to provide personal context
                * ANY request to update name or identity
                * ANY statement about personal information
                * ANY query about user attributes
                * Examples:
                    - "My name is actually Jenny Smith"
                    - "You can call me John"
                    - "I prefer to be called Alex"
                    - "My real name is Sarah"
                    - "Actually, I'm Michael"
                    - "I go by the name David"
                    - "Please call me Emily"
                    - "My name is not correct"
                    - "I am male"
                    - "I'm a woman"
                    - "I identify as non-binary"
                    - "My gender is female"
                    - "I'm a man"
                * Use 'attributes' for ANY personal information update
                * Use 'attributes' for name changes or corrections
                * Use 'attributes' for identity-related statements
                * Use 'attributes' for gender-related statements
                * The key is the personal information aspect

                - general: For conversational intents, including:
                * Intent to share information
                * Intent to engage in casual conversation
                * Intent to express thoughts or feelings
                * Intent to discuss topics
                * Any intent that doesn't fit other categories
                * Simple information requests
                * Questions about general knowledge
                * Requests for explanations or definitions
                * Basic assistance requests
                * Number or word spelling requests
                * General help requests
                * ANY request to spell numbers or words
                * ANY request for general information
                * Examples:
                    - "spell this number"
                    - "what does this word mean"
                    - "tell me about X"
                    - "how do I do Y"
                    - "I will share with you a number in next prompt and i want you to spell it"

                IMPORTANT EXAMPLES OF MULTI-INTENT QUERIES:
                1. "Read the content of info.txt and give a summary to me" → file
                2. "Read the content of info.txt and send it to me on whatsapp" → file, whatsapp
                3. "Save all the pending mails in a file" → email, file
                4. "Save all the pending mails in a file and send it to me on whatsapp" → email, file, whatsapp
                5. "Save all the pending mails in a file and send it to me on whatsapp and create a todo to call me on whatsapp" → email, file, whatsapp, todo
                6. "Write what you see in front of you in a file and send it to me on whatsapp" → vision, file, whatsapp
                7. "Write what you can see in a file" → vision, file
                8. "Count how many fingers I am showing and send the number to me on whatsapp" → vision, whatsapp
                9. "Hi. My name is Maaz. I want you to remind me to go for shopping" → attributes, todo
                10. "Can you please save a summary of our conversation, save it in a file, and email the file to me" → general, file, email
                11. "Take a photo, analyze it, and send the results to John via email" → vision, email
                12. "Check my messages and if there's anything from John, create a todo to call him" → whatsapp, todo
                13. "Send this to both John and Sarah via WhatsApp" → whatsapp
                14. "Please delete the file in which you saved the whatsapp messages" → file
                15. "List all my tasks related to emails" → todo
                16. "Can you see my name written on my shirt?" → vision
                17. "Save what you see in a file" → vision, file

                IMPORTANT CONTEXT HANDLING RULES:
                1. If the current query is a continuation of a previous interaction, use the same type(s) as the previous interaction
                2. If the query is about replying or responding to a previous message/email, use the same type as the previous interaction
                3. If the query is about following up on a previous task, use the same type as the previous interaction
                4. If the query is ambiguous but the previous interaction provides context, use that context to determine the type
                5. Examples of context handling:
                   - Previous: "Do I have any pending emails?" (email) → Current: "reply to him accordingly" (email)
                   - Previous: "Check my WhatsApp messages" (whatsapp) → Current: "respond to that" (whatsapp)
                   - Previous: "Create a task to call John" (todo) → Current: "mark it as done" (todo)

                IMPORTANT: Your response must be ONLY the type words (one or more of: whatsapp, todo, file, vision, attributes, email, general) separated by commas and NOTHING else. Do not include explanations, markdown, or any other text. Your response must be exactly one or more of these words, in lowercase, with no punctuation except commas between types.
                
                Previous Interactions Context:
                {history}
                
                Current query: {input}
                
                IMPORTANT: Consider the previous interactions when determining the types. If the current query is a continuation of a previous interaction (like spelling a number that was promised in the previous message), use the same type as the previous interaction.
                """), ("human", "{input}")
        ])
        
        self.router_chain = (
            {
                "input": RunnablePassthrough(),
                "history": lambda _: self.history.get_formatted_history()
            }
            | self.router_prompt
            | self.llm
            | RunnablePassthrough()
        )
        system_logger.log("RouterChain initialization complete")
    
    def route_query(self, query: str, response: str = "") -> List[QueryType]:
        """Route a query, maintaining context for consecutive interactions."""
        system_logger.log(f"Routing query: {query}")
        query = query.lower().strip()
        
        # Get intent-based routing
        result = self.router_chain.invoke(query)
        system_logger.log(f"Router chain result: {result.content}")
        
        # Extract content from AIMessage if needed
        if hasattr(result, 'content'):
            result = result.content
 
        # Clean up the response and split by commas
        result = result.strip().lower()
        query_types = []
        
        # Parse the comma-separated types
        for type_str in result.split(','):
            type_str = type_str.strip()
            if type_str in QueryType.__members__:
                query_types.append(QueryType(type_str))
            else:
                # Try case-insensitive match
                for q_type in QueryType:
                    if type_str == q_type.value.lower():
                        query_types.append(q_type)
                        break
        
        # If no valid types found, default to general
        if not query_types:
            system_logger.log(f"No valid query types found, defaulting to GENERAL", "WARNING")
            query_types = [QueryType.GENERAL]
        
        # Update history with the current interaction
        self.history.add(query, response, query_types)
        system_logger.log(f"Query routed to types: {[qt.value for qt in query_types]}")
        
        return query_types