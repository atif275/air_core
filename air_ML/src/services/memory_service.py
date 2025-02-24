from typing import Dict, Any, Optional, Union
from dataclasses import asdict
from src.conversation.memory_interface import ChatMemoryInterface
from src.conversation.memory import ChatMemory
from src.types.person import PersonData

class MemoryService:
    def __init__(self, memory: ChatMemoryInterface = None):
        self.memory = memory or ChatMemory()

    def update_memory(self, person_id: int, data: Union[Dict[str, Any], PersonData, Any]) -> None:
        """Update the memory for a person with new data."""
        if isinstance(data, PersonData):
            # Convert PersonData to dictionary
            data = asdict(data)
        
        if isinstance(data, dict):
            current_data = self.memory.get_active_person(person_id) or {}
            current_data.update(data)
            self.memory.set_active_person(person_id, current_data)
        else:
            # For non-dict data, just set it directly
            self.memory.set_active_person(person_id, data)
        print(f"[DEBUG] Updated Memory with New Data: {data}")

    def get_from_memory(self, person_id: int) -> Optional[Union[PersonData, Any]]:
        """Get person data from memory."""
        data = self.memory.get_active_person(person_id)
        if isinstance(data, dict) and 'id' in data:
            # Convert dictionary back to PersonData
            return PersonData(**data)
        return data

    def clear_memory(self, person_id: int) -> None:
        """Clear the memory for a person."""
        self.memory.set_active_person(person_id, None)

# Create a global instance
memory_service = MemoryService() 