"""Session management module for the chatbot."""
from typing import Optional
from datetime import datetime
from ..database.database import get_database, Person, Active
from .interfaces import IMemoryManager

class SessionManager:
    """Manages user sessions and active person state."""
    
    def __init__(self, memory_manager: Optional[IMemoryManager] = None):
        """Initialize the session manager."""
        self.db = get_database()
        self.memory_manager = memory_manager
        self.current_person = None
        self._initialize_session()

    def _initialize_session(self):
        """Initialize the session with the active person and memory."""
        self.current_person = self._get_active_person()
        # Only initialize memory if we have a memory manager
        if self.current_person and self.memory_manager:
            self.memory_manager.initialize_memory(self.current_person)

    def _get_active_person(self) -> Optional[Person]:
        """Get the currently active person from the database."""
        print(f"\n=== Getting Active Person from Database ===")
        active = self.db.query(Active).filter(Active.is_active == True).first()
        if active:
            print(f"Found active person: ID={active.person_id}")
            return active.person
        print("No active person found in database")
        return None

    def get_active_user_id(self) -> Optional[int]:
        """Get the ID of the currently active user."""
        person = self._get_active_person()
        return person.id if person else None

    def get_current_person(self) -> Optional[Person]:
        """Get the current active person."""
        print(f"\n=== Getting Current Person ===")
        print(f"Cached current person: {self.current_person.id if self.current_person else None}")
        
        # Always get fresh from database to ensure accuracy
        active_person = self._get_active_person()
        print(f"Active person from DB: {active_person.id if active_person else None}")
        
        # Update cache if different
        if active_person and (not self.current_person or self.current_person.id != active_person.id):
            print(f"Updating cached person from {self.current_person.id if self.current_person else None} to {active_person.id}")
            self.current_person = active_person
            # Ensure memory is initialized for new person
            try:
                self.memory_manager.initialize_memory(self.current_person)
                print("Initialized memory for new person")
            except Exception as e:
                print(f"ERROR initializing memory: {str(e)}")
                import traceback
                print(f"Full traceback: {traceback.format_exc()}")
                return None
        
        return self.current_person

    def switch_active_person(self, person_id: int) -> bool:
        """
        Switch the active person to the specified person ID.
        Returns True if successful, False otherwise.
        """
        print(f"\n=== Switching Active Person to {person_id} ===")
        try:
            # Store old person's ID before switching
            old_person_id = self.current_person.id if self.current_person else None
            print(f"Current active person: {old_person_id}")
            
            # Clear any existing active records
            self.db.query(Active).update({"is_active": False})
            self.db.commit()
            print("Cleared existing active records")
            
            # Set new active person
            active = Active(
                person_id=person_id,
                is_active=True,
                last_active=datetime.utcnow()
            )
            self.db.add(active)
            self.db.commit()
            print(f"Set new active person: {person_id}")
            
            # Force reload of current person from database
            self.current_person = None  # Clear cached person
            self.current_person = self._get_active_person()  # Reload from DB
            print(f"Reloaded current person from DB: {self.current_person.id if self.current_person else None}")
            
            if not self.current_person:
                print("ERROR: Failed to load current person after switch")
                return False
            
            # Initialize fresh memory with current context
            try:
                self.memory_manager.initialize_memory(self.current_person)
                print("Initialized fresh memory for new person")
            except Exception as e:
                print(f"ERROR initializing memory: {str(e)}")
                import traceback
                print(f"Full traceback: {traceback.format_exc()}")
                return False
            
            # Ensure old person's memory is marked for cleanup
            if old_person_id and old_person_id in self.memory_manager.memory_last_used:
                # Don't update last_used timestamp for old person
                # This will allow it to become inactive after 1 minute
                print(f"Marked person {old_person_id} for cleanup")
            
            return True
        except Exception as e:
            print(f"ERROR switching active person: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            self.db.rollback()
            return False

    def set_memory_manager(self, memory_manager: IMemoryManager) -> None:
        """Set the memory manager after initialization."""
        self.memory_manager = memory_manager
        # Initialize memory for current person if we have one
        if self.current_person:
            self.memory_manager.initialize_memory(self.current_person) 