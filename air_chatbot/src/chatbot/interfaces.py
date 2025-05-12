"""Interface definitions for chatbot components."""
from typing import Protocol, Optional
from datetime import datetime
from langchain.memory import ConversationBufferMemory
from ..database.database import Person

class IMemoryManager(Protocol):
    """Interface for memory management operations."""
    def initialize_memory(self, person: Person) -> None:
        """Initialize memory for a person."""
        ...

    def get_memory(self, person_id: int) -> Optional[ConversationBufferMemory]:
        """Get memory for a person."""
        ...

    def update_memory_timestamp(self, person_id: int) -> None:
        """Update memory timestamp."""
        ...

class ISessionManager(Protocol):
    """Interface for session management operations."""
    def get_current_person(self) -> Optional[Person]:
        """Get current active person."""
        ...

    def switch_active_person(self, person_id: int) -> bool:
        """Switch active person."""
        ... 