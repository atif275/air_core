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

class ConversationSummary(TypedDict):
    summary: str
    start_time: datetime
    end_time: datetime

class MemoryManager(IMemoryManager):
    def __init__(self, llm: ChatOpenAI):
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

    def set_session_manager(self, session_manager: ISessionManager) -> None:
        """Set the session manager and start the background cleanup thread."""
        self._session_manager = session_manager
        # Start the background thread only after session manager is set
        if not self.cleanup_thread:
            self.cleanup_thread = threading.Thread(target=self._background_cleanup, daemon=True)
            self.cleanup_thread.start()

    def _background_cleanup(self):
        """Background thread that periodically checks for and cleans up inactive memories."""
        while True:
            try:
                self._cleanup_inactive_memories()
            except Exception as e:
                print(f"Error in background cleanup: {str(e)}")
            time.sleep(60)  # Check every minute

    def _cleanup_inactive_memories(self):
        """Clean up memories that haven't been used for over 1 minute."""
        print("\n=== Starting Memory Cleanup Process ===")
        
        if not self._session_manager:
            print("ERROR: Session manager not set in memory manager")
            return
            
        current_time = datetime.utcnow()
        inactive_persons = []

        print("\nChecking for inactive memories...")
        print(f"Current time: {current_time}")
        print(f"Memory last used entries: {self.memory_last_used}")
        
        for person_id, last_used in self.memory_last_used.items():
            print(f"\nProcessing person {person_id}:")
            print(f"Last used time: {last_used}")
            
            # Skip the current active person
            active_person = self._session_manager.get_current_person()
            if not active_person:
                print("WARNING: No active person found in session manager")
                continue
                
            print(f"Active person ID: {active_person.id}")
            
            if person_id == active_person.id:
                print(f"SKIPPING: Person {person_id} is currently active")
                continue

            # Check if memory is older than 1 minute
            inactive_time = (current_time - last_used).total_seconds()
            print(f"Inactive time: {inactive_time:.1f} seconds")
            
            if inactive_time > 60:
                print(f"Person {person_id} is inactive for more than 1 minute")
                # Create and save summary before clearing
                if person_id in self.memories:
                    print(f"Creating summary for inactive person {person_id}")
                    print(f"Memory state before cleanup for person {person_id}:")
                    print(f"- Has memory: {person_id in self.memories}")
                    print(f"- Has last used: {person_id in self.memory_last_used}")
                    print(f"- Has start index: {person_id in self.conversation_start_indices}")
                    
                    try:
                        self._save_memory_summary(person_id)
                        print(f"Successfully saved summary for person {person_id}")
                        inactive_persons.append(person_id)
                    except Exception as e:
                        print(f"ERROR saving summary for person {person_id}: {str(e)}")
                else:
                    print(f"WARNING: No memory found for person {person_id}")
            else:
                print(f"Person {person_id} is inactive but not yet ready for cleanup")

        # Remove inactive memories and their tracking data
        for person_id in inactive_persons:
            print(f"\nCleaning up memory for person {person_id}")
            try:
                self._cleanup_person_data(person_id)
                print(f"Successfully cleaned up person {person_id}")
            except Exception as e:
                print(f"ERROR cleaning up person {person_id}: {str(e)}")
        
        print("\n=== Memory Cleanup Process Complete ===\n")

    def _cleanup_person_data(self, person_id: int) -> None:
        """Clean up memory data for a specific person."""
        print(f"\n=== Cleaning up data for person {person_id} ===")
        try:
            # Remove memory and last used entries
            if person_id in self.memories:
                print(f"Removing memory for person {person_id}")
                del self.memories[person_id]
            if person_id in self.memory_last_used:
                print(f"Removing last used entry for person {person_id}")
                del self.memory_last_used[person_id]
            if person_id in self.conversation_start_indices:
                print(f"Removing start index for person {person_id}")
                del self.conversation_start_indices[person_id]
            
            print(f"Successfully cleaned up data for person {person_id}")
        except Exception as e:
            print(f"Error cleaning up person data: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")

    def _save_memory_summary(self, person_id: int):
        """Create a summary of only the new conversation and save it to the database."""
        print(f"\n=== Starting Memory Summary Save for Person {person_id} ===")
        
        if person_id not in self.memories or person_id not in self.conversation_start_indices:
            print(f"ERROR: Missing required data for person {person_id}")
            print(f"- Has memory: {person_id in self.memories}")
            print(f"- Has start index: {person_id in self.conversation_start_indices}")
            return

        memory = self.memories[person_id]
        messages = memory.chat_memory.messages

        # Get only the new messages that occurred after initialization
        start_idx = self.conversation_start_indices[person_id]
        new_conversation_messages = messages[start_idx:]
        
        print(f"Total messages: {len(messages)}")
        print(f"Start index: {start_idx}")
        print(f"New messages to summarize: {len(new_conversation_messages)}")
        
        if not new_conversation_messages:
            print("No new messages to summarize")
            return

        # Create a summary prompt for only the new conversation
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
            # Generate summary using the LLM
            print("Generating summary with LLM...")
            summary = self.llm.predict(summary_prompt)
            print(f"Generated summary length: {len(summary)}")

            # Save to database using conversation manager
            print("Saving summary to database...")
            self.conversation_manager.add_conversation_summary(person_id, summary)
            print("Successfully saved summary to database")
        except Exception as e:
            print(f"ERROR in summary generation/saving: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
        
        print(f"=== Memory Summary Save Complete for Person {person_id} ===\n")

    def initialize_memory(self, person: Person):
        """Initialize the conversation memory for a person."""
        memory = ConversationBufferMemory(
            return_messages=True,
            input_key="input",
            output_key="response",
            memory_key="chat_history"
        )
        
        # Get conversation history and create personality prompt
        conversation_history = self.conversation_manager.format_conversation_history(person.id)
        system_prompt = self.personality_manager.create_personality_prompt(person, conversation_history)
        
        memory.chat_memory.add_message(SystemMessage(content=system_prompt))
        memory.chat_memory.add_message(AIMessage(content=f"Hello {person.name}! I'm here to chat with you."))
        
        self.memories[person.id] = memory
        self.memory_last_used[person.id] = datetime.utcnow()
        # Track the point where new conversation starts (after system message and greeting)
        self.conversation_start_indices[person.id] = len(memory.chat_memory.messages)

    def update_memory_timestamp(self, person_id: int) -> None:
        """Update the last used timestamp for a person's memory."""
        self.memory_last_used[person_id] = datetime.utcnow()

    def get_memory(self, person_id: int) -> Optional[ConversationBufferMemory]:
        """Get the memory for a person."""
        return self.memories.get(person_id)

    def get_memory_ids(self) -> List[int]:
        """Get list of person IDs with active memories."""
        return list(self.memories.keys())

    def clear_memory(self, person_id: int) -> None:
        """Clear memory for a person."""
        if person_id in self.memories:
            self._save_memory_summary(person_id)
            self._cleanup_person_data(person_id)

    def update_last_active_check(self) -> None:
        """Update the timestamp of the last active check."""
        self.last_active_check = datetime.utcnow() 