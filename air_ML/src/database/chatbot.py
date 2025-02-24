from src.database.memory_operations import update_memory, get_from_memory, clear_memory
# ... rest of imports ...

class OpenAIChatBot:
    def respond(self, user_input):
        # ... existing code ...
        if last_active_person != active_person_id:
            clear_memory(active_person_id)
        
        person_data = get_from_memory(active_person_id)
        # ... rest of the method ... 