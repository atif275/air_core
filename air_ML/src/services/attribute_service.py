from typing import Dict, Optional
from src.database.db_operations import db_ops
from src.services.memory_service import memory_service

def extract_and_update_person_attributes(active_person_id: int, assistant_reply: str) -> Optional[Dict]:
    """Extract attributes from assistant reply and update both database and memory."""
    extracted_data = {}
    
    for attribute in ["NAME", "AGE", "ETHNICITY"]:
        if attribute + "=" in assistant_reply:
            value = assistant_reply.split(attribute + "=")[1].split('\n')[0].strip()
            extracted_data[attribute.lower()] = value
            db_ops.update_person_attribute(active_person_id, attribute.lower(), value)
    
    if extracted_data:
        memory_service.update_memory(active_person_id, extracted_data)
        return extracted_data
    
    return None 