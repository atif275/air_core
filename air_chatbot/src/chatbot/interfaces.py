"""Interface definitions for chatbot components."""
from typing import Protocol, Optional
from datetime import datetime
from langchain.memory import ConversationBufferMemory
from ..database.database import Person

class IMemoryManager(Protocol):
    """Interface for memory management operations.
    
    Implementers should log the following:
    - Memory initialization attempts and results
    - Memory retrieval operations
    - Memory timestamp updates
    - Any errors during memory operations
    """
    def initialize_memory(self, person: Person) -> None:
        """Initialize memory for a person.
        
        Should log:
        - Start of initialization
        - Success/failure of initialization
        - Any errors during initialization
        """
        ...

    def get_memory(self, person_id: int) -> Optional[ConversationBufferMemory]:
        """Get memory for a person.
        
        Should log:
        - Memory retrieval attempt
        - Whether memory was found
        - Any errors during retrieval
        """
        ...

    def update_memory_timestamp(self, person_id: int) -> None:
        """Update memory timestamp.
        
        Should log:
        - Timestamp update attempt
        - Success/failure of update
        - Any errors during update
        """
        ...

class ISessionManager(Protocol):
    """Interface for session management operations.
    
    Implementers should log the following:
    - Session state changes
    - Person switching operations
    - Current person retrieval
    - Any errors during session operations
    """
    def get_current_person(self) -> Optional[Person]:
        """Get current active person.
        
        Should log:
        - Current person retrieval attempt
        - Whether a person was found
        - Any errors during retrieval
        """
        ...

    def switch_active_person(self, person_id: int) -> bool:
        """Switch active person.
        
        Should log:
        - Person switch attempt
        - Success/failure of switch
        - Any errors during switch
        """
        ... 