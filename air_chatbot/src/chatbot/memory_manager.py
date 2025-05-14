"""Memory management module for the chatbot."""
from typing import Dict, List, Optional, TypedDict
from datetime import datetime
import threading
import time
import json
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from ..database.database import get_database, Person, Active, Conversation
from .personality_manager import PersonalityManager
from .conversation_manager import ConversationManager
from .interfaces import ISessionManager, IMemoryManager
from .logger import system_logger

class ConversationSummary(TypedDict):
    summary: str
    start_time: datetime
    end_time: datetime

class MemoryManager(IMemoryManager):
    def __init__(self, llm: ChatOpenAI):
        system_logger.log("Initializing MemoryManager", "INFO", is_memory_log=True)
        self.llm = llm
        self.db = get_database()
        self.memories = {}
        self.memory_last_used = {}
        self.conversation_start_indices = {}
        self.last_active_check = None
        self.personality_manager = PersonalityManager()
        self.conversation_manager = ConversationManager()
        self._session_manager: Optional[ISessionManager] = None
        self.cleanup_thread = None  # Don't start thread yet
        system_logger.log("MemoryManager initialized successfully", "INFO", is_memory_log=True)

    def set_session_manager(self, session_manager: ISessionManager) -> None:
        """Set the session manager and start the background cleanup thread."""
        system_logger.log("Setting session manager and starting cleanup thread", "INFO", is_memory_log=True)
        self._session_manager = session_manager
        # Start the background thread only after session manager is set
        if not self.cleanup_thread:
            self.cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
            self.cleanup_thread.start()
            system_logger.log("Cleanup thread started", "INFO", is_memory_log=True)

    def _background_cleanup(self):
        """Background thread that periodically checks for and cleans up inactive memories."""
        system_logger.log("Starting background cleanup thread", "INFO", is_memory_log=True)
        while True:
            try:
                self._cleanup_inactive_memories()
            except Exception as e:
                system_logger.log(f"Error in background cleanup: {str(e)}", "ERROR", is_memory_log=True)
            time.sleep(60)  # Check every minute

    def _cleanup_inactive_memories(self):
        """Clean up memories that haven't been used for over 1 minute."""
        system_logger.log("Starting memory cleanup process", "INFO", is_memory_log=True)
        
        if not self._session_manager:
            system_logger.log("Session manager not set in memory manager", "ERROR", is_memory_log=True)
            return
            
        current_time = datetime.utcnow()
        inactive_persons = []

        system_logger.log(f"Checking for inactive memories at {current_time}", "INFO", is_memory_log=True)
        
        # Create a copy of the items to avoid dictionary changed size during iteration
        memory_items = list(self.memory_last_used.items())
        
        for person_id, last_used in memory_items:
            system_logger.log(f"Processing person {person_id}, last used: {last_used}", "INFO", is_memory_log=True)
            
            # Skip the current active person
            active_person = self._session_manager.get_current_person()
            if not active_person:
                system_logger.log("No active person found in session manager", "WARNING", is_memory_log=True)
                continue
                
            if person_id == active_person.id:
                system_logger.log(f"Person {person_id} is currently active, skipping", "INFO", is_memory_log=True)
                continue

            # Check if memory is older than 1 minute
            inactive_time = (current_time - last_used).total_seconds()
            
            if inactive_time > 60:
                system_logger.log(f"Person {person_id} is inactive for {inactive_time:.1f} seconds", "INFO", is_memory_log=True)
                if person_id in self.memories:
                    try:
                        self._save_memory_summary(person_id)
                        system_logger.log(f"Successfully saved summary for person {person_id}", "INFO", is_memory_log=True)
                        inactive_persons.append(person_id)
                    except Exception as e:
                        system_logger.log(f"Error saving summary for person {person_id}: {str(e)}", "ERROR", is_memory_log=True)
                else:
                    system_logger.log(f"No memory found for person {person_id}", "WARNING", is_memory_log=True)
            else:
                system_logger.log(f"Person {person_id} is inactive but not yet ready for cleanup", "INFO", is_memory_log=True)

        # Remove inactive memories and their tracking data
        for person_id in inactive_persons:
            try:
                self._cleanup_person_data(person_id)
                system_logger.log(f"Successfully cleaned up person {person_id}", "INFO", is_memory_log=True)
            except Exception as e:
                system_logger.log(f"Error cleaning up person {person_id}: {str(e)}", "ERROR", is_memory_log=True)
        
        system_logger.log("Memory cleanup process complete", "INFO", is_memory_log=True)

    def _cleanup_person_data(self, person_id: int) -> None:
        """Clean up memory data for a specific person."""
        system_logger.log(f"Cleaning up data for person {person_id}", "INFO", is_memory_log=True)
        try:
            if person_id in self.memories:
                del self.memories[person_id]
                system_logger.log(f"Removed memory for person {person_id}", "INFO", is_memory_log=True)
            if person_id in self.memory_last_used:
                del self.memory_last_used[person_id]
                system_logger.log(f"Removed last used entry for person {person_id}", "INFO", is_memory_log=True)
            if person_id in self.conversation_start_indices:
                del self.conversation_start_indices[person_id]
                system_logger.log(f"Removed start index for person {person_id}", "INFO", is_memory_log=True)
            
            system_logger.log(f"Successfully cleaned up data for person {person_id}", "INFO", is_memory_log=True)
        except Exception as e:
            system_logger.log(f"Error cleaning up person data: {str(e)}", "ERROR", is_memory_log=True)

    def _save_memory_summary(self, person_id: int):
        """Create a summary of only the new conversation and save it to the database."""
        system_logger.log(f"Starting memory summary save for person {person_id}", "INFO", is_memory_log=True)
        
        if person_id not in self.memories or person_id not in self.conversation_start_indices:
            system_logger.log(f"Missing required data for person {person_id}", "ERROR", is_memory_log=True)
            return

        memory = self.memories[person_id]
        messages = memory.chat_memory.messages
        start_idx = self.conversation_start_indices[person_id]
        new_conversation_messages = messages[start_idx:]
        
        system_logger.log(f"Processing {len(new_conversation_messages)} new messages for summary", "INFO", is_memory_log=True)
        
        if not new_conversation_messages:
            system_logger.log("No new messages to summarize", "INFO", is_memory_log=True)
            return

        conversation_text = ' '.join([f"{m.type}: {m.content}" for m in new_conversation_messages])
        summary_prompt = f"""Create a concise and accurate summary of the conversation. Follow these guidelines:

        1. Focus on the actual information exchanged, not assumptions or inferences
        2. Maintain chronological order of events
        3. Include corrections or clarifications that were made
        4. Don't add information that wasn't explicitly mentioned
        5. If the conversation involves personal information about others (like family members), clearly distinguish between the user's own information and information about others
        6. Include any important context or background information that was shared
        7. If there were any misunderstandings or corrections, include those
        8. Keep the summary objective and factual

        Conversation:
        {conversation_text}

        Remember: Only include information that was explicitly shared in the conversation. Don't make assumptions or add information that wasn't mentioned."""

        try:
            system_logger.log("Generating summary with LLM", "INFO", is_memory_log=True)
            summary = self.llm.predict(summary_prompt)
            system_logger.log(f"Generated summary of length {len(summary)}", "INFO", is_memory_log=True)

            system_logger.log("Saving summary to database", "INFO", is_memory_log=True)
            self.conversation_manager.add_conversation_summary(person_id, summary)
            system_logger.log("Successfully saved summary to database", "INFO", is_memory_log=True)
        except Exception as e:
            system_logger.log(f"Error in summary generation/saving: {str(e)}", "ERROR", is_memory_log=True)
        
        system_logger.log(f"Memory summary save complete for person {person_id}", "INFO", is_memory_log=True)

    def initialize_memory(self, person: Person):
        """Initialize the conversation memory for a person."""
        system_logger.log(f"Initializing memory for person {person.id}", "INFO", is_memory_log=True)
        
        # If memory already exists, don't reinitialize
        if person.id in self.memories:
            system_logger.log(f"Memory already exists for person {person.id}, updating timestamp", "INFO", is_memory_log=True)
            self.update_memory_timestamp(person.id)
            return
            
        memory = ConversationBufferMemory(
            return_messages=True,
            input_key="input",
            output_key="response",
            memory_key="chat_history"
        )
        
        conversation_history = self.conversation_manager.format_conversation_history(person.id)
        system_prompt = self.personality_manager.create_personality_prompt(person, conversation_history)
        
        memory.chat_memory.add_message(SystemMessage(content=system_prompt))
        memory.chat_memory.add_message(AIMessage(content=f"Hello {person.name}! I'm here to chat with you."))
        
        self.memories[person.id] = memory
        self.memory_last_used[person.id] = datetime.utcnow()
        self.conversation_start_indices[person.id] = len(memory.chat_memory.messages)
        system_logger.log(f"Memory initialized for person {person.id}", "INFO", is_memory_log=True)

    def update_memory_timestamp(self, person_id: int) -> None:
        """Update the last used timestamp for a person's memory."""
        system_logger.log(f"Updating memory timestamp for person {person_id}", "INFO", is_memory_log=True)
        self.memory_last_used[person_id] = datetime.utcnow()

    def get_memory(self, person_id: int) -> Optional[ConversationBufferMemory]:
        """Get the memory for a person."""
        system_logger.log(f"Retrieving memory for person {person_id}", "INFO", is_memory_log=True)
        memory = self.memories.get(person_id)
        if memory:
            system_logger.log(f"Memory found for person {person_id}", "INFO", is_memory_log=True)
        else:
            system_logger.log(f"No memory found for person {person_id}", "WARNING", is_memory_log=True)
        return memory

    def get_memory_ids(self) -> List[int]:
        """Get list of person IDs with active memories."""
        system_logger.log("Retrieving list of active memory IDs", "INFO", is_memory_log=True)
        return list(self.memories.keys())

    def clear_memory(self, person_id: int) -> None:
        """Clear memory for a person."""
        system_logger.log(f"Clearing memory for person {person_id}", "INFO", is_memory_log=True)
        if person_id in self.memories:
            self._save_memory_summary(person_id)
            self._cleanup_person_data(person_id)
            system_logger.log(f"Memory cleared for person {person_id}", "INFO", is_memory_log=True)
        else:
            system_logger.log(f"No memory to clear for person {person_id}", "WARNING", is_memory_log=True)

    def update_last_active_check(self) -> None:
        """Update the timestamp of the last active check."""
        system_logger.log("Updating last active check timestamp", "INFO", is_memory_log=True)
        self.last_active_check = datetime.utcnow()

    def update_memory(self, person_id: int, user_input: str, response: str) -> None:
        """Update the conversation memory with a new interaction."""
        system_logger.log(f"Updating memory for person {person_id}", "INFO", is_memory_log=True)
        
        if person_id not in self.memories:
            system_logger.log(f"No memory found for person {person_id}", "WARNING", is_memory_log=True)
            return
            
        memory = self.memories[person_id]
        memory.chat_memory.add_user_message(user_input)
        memory.chat_memory.add_ai_message(response)
        self.update_memory_timestamp(person_id)
        system_logger.log(f"Memory updated for person {person_id}", "INFO", is_memory_log=True) 