from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class PersonData:
    id: Optional[int] = None
    name: str = "Unknown"
    age: Optional[int] = None
    gender: Optional[str] = None
    emotion: Optional[str] = None
    ethnicity: Optional[str] = None 