"""Session management module for the chatbot."""
from typing import Optional
from datetime import datetime
from ..database.database import get_database, Person, Active
from .interfaces import IMemoryManager
from .logger import system_logger

class SessionManager:
    """Manages user sessions and active person state."""
    
    def __init__(self, memory_manager: Optional[IMemoryManager] = None):
        """Initialize the session manager."""
        system_logger.log("Initializing SessionManager", "INFO", is_memory_log=True)
        self.db = get_database()
        self.memory_manager = memory_manager
        self.current_person = None
        self._initialize_session()
        system_logger.log("SessionManager initialized", "INFO", is_memory_log=True)

    def _initialize_session(self):
        """Initialize the session with the active person and memory."""
        system_logger.log("Initializing session", "INFO", is_memory_log=True)
        self.current_person = self._get_active_person()
        # Only initialize memory if we have a memory manager
        if self.current_person and self.memory_manager:
            try:
                self.memory_manager.initialize_memory(self.current_person)
                system_logger.log(f"Initialized memory for person {self.current_person.id}", "INFO", is_memory_log=True)
            except Exception as e:
                system_logger.log(f"Error initializing memory: {str(e)}", "ERROR", is_memory_log=True)

    def _get_active_person(self) -> Optional[Person]:
        """Get the currently active person from the database."""
        system_logger.log("Getting active person from database", "INFO", is_memory_log=True)
        active = self.db.query(Active).filter(Active.is_active == True).first()
        if active:
            system_logger.log(f"Found active person: ID={active.person_id}", "INFO", is_memory_log=True)
            return active.person
        system_logger.log("No active person found in database", "WARNING", is_memory_log=True)
        return None

    def get_active_user_id(self) -> Optional[int]:
        """Get the ID of the currently active user."""
        system_logger.log("Getting active user ID", "INFO", is_memory_log=True)
        person = self._get_active_person()
        if person:
            system_logger.log(f"Active user ID: {person.id}", "INFO", is_memory_log=True)
        else:
            system_logger.log("No active user found", "WARNING", is_memory_log=True)
        return person.id if person else None

    def get_current_person(self) -> Optional[Person]:
        """Get the current active person."""
        system_logger.log("Getting current person", "INFO", is_memory_log=True)
        system_logger.log(f"Cached current person: {self.current_person.id if self.current_person else None}", "INFO", is_memory_log=True)
        
        # Always get fresh from database to ensure accuracy
        active_person = self._get_active_person()
        system_logger.log(f"Active person from DB: {active_person.id if active_person else None}", "INFO", is_memory_log=True)
        
        # Update cache if different
        if active_person and (not self.current_person or self.current_person.id != active_person.id):
            system_logger.log(f"Updating cached person from {self.current_person.id if self.current_person else None} to {active_person.id}", "INFO", is_memory_log=True)
            self.current_person = active_person
            # Ensure memory is initialized for new person
            try:
                self.memory_manager.initialize_memory(self.current_person)
                system_logger.log("Initialized memory for new person", "INFO", is_memory_log=True)
            except Exception as e:
                system_logger.log(f"Error initializing memory: {str(e)}", "ERROR", is_memory_log=True)
                return None
        
        return self.current_person

    def switch_active_person(self, person_id: int) -> bool:
        """
        Switch the active person to the specified person ID.
        Returns True if successful, False otherwise.
        """
        system_logger.log(f"Switching active person to {person_id}", "INFO", is_memory_log=True)
        try:
            # Store old person's ID before switching
            old_person_id = self.current_person.id if self.current_person else None
            system_logger.log(f"Current active person: {old_person_id}", "INFO", is_memory_log=True)
            
            # Clear any existing active records
            self.db.query(Active).update({"is_active": False})
            self.db.commit()
            system_logger.log("Cleared existing active records", "INFO", is_memory_log=True)
            
            # Set new active person
            active = Active(
                person_id=person_id,
                is_active=True,
                last_active=datetime.utcnow()
            )
            self.db.add(active)
            self.db.commit()
            system_logger.log(f"Set new active person: {person_id}", "INFO", is_memory_log=True)
            
            # Force reload of current person from database
            self.current_person = None  # Clear cached person
            self.current_person = self._get_active_person()  # Reload from DB
            system_logger.log(f"Reloaded current person from DB: {self.current_person.id if self.current_person else None}", "INFO", is_memory_log=True)
            
            if not self.current_person:
                system_logger.log("Failed to load current person after switch", "ERROR", is_memory_log=True)
                return False
            
            # Initialize fresh memory with current context
            try:
                self.memory_manager.initialize_memory(self.current_person)
                system_logger.log("Initialized fresh memory for new person", "INFO", is_memory_log=True)
            except Exception as e:
                system_logger.log(f"Error initializing memory: {str(e)}", "ERROR", is_memory_log=True)
                return False
            
            # Ensure old person's memory is marked for cleanup
            if old_person_id and old_person_id in self.memory_manager.memory_last_used:
                system_logger.log(f"Marked person {old_person_id} for cleanup", "INFO", is_memory_log=True)
            
            system_logger.log("Successfully switched active person", "INFO", is_memory_log=True)
            return True
        except Exception as e:
            system_logger.log(f"Error switching active person: {str(e)}", "ERROR", is_memory_log=True)
            self.db.rollback()
            return False

    def set_memory_manager(self, memory_manager: IMemoryManager) -> None:
        """Set the memory manager after initialization."""
        system_logger.log("Setting memory manager", "INFO", is_memory_log=True)
        self.memory_manager = memory_manager
        # Initialize memory for current person if we have one
        if self.current_person:
            try:
                self.memory_manager.initialize_memory(self.current_person)
                system_logger.log(f"Initialized memory for current person {self.current_person.id}", "INFO", is_memory_log=True)
            except Exception as e:
                system_logger.log(f"Error initializing memory: {str(e)}", "ERROR", is_memory_log=True) 