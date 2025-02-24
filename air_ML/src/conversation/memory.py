from typing import Dict, Any, Optional
from .memory_interface import ChatMemoryInterface

class ChatMemory(ChatMemoryInterface):
    def __init__(self):
        self._memory = {}

    def get_active_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        return self._memory.get(str(person_id))

    def set_active_person(self, person_id: int, data: Optional[Dict[str, Any]]) -> None:
        self._memory[str(person_id)] = data

chat_memory = ChatMemory()
