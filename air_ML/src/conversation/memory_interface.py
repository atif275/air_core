from typing import Dict, Any, Optional

class ChatMemoryInterface:
    def get_active_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set_active_person(self, person_id: int, data: Optional[Dict[str, Any]]) -> None:
        raise NotImplementedError 