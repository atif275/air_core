from typing import Dict, Optional
import random
from langchain.schema import HumanMessage, AIMessage
from ..attributes_management.attributes_management import determine_age_group, get_casual_expressions
from .memory_manager import MemoryManager
from .router import QueryType, RouterChain

class ResponseManager:
    def __init__(self, memory_manager: MemoryManager, router: RouterChain):
        """Initialize the response manager."""
        self.memory_manager = memory_manager
        self.router = router

    def format_attribute_updates(self, attributes: Dict[str, str]) -> str:
        """Format attribute updates into a natural response."""
        updates = []
        if attributes.get("name"):
            updates.append(f"I'll remember your name is {attributes['name']}")
        if attributes.get("age"):
            updates.append(f"I've noted that you're {attributes['age']} years old")
        if attributes.get("ethnicity"):
            updates.append(f"I understand you're {attributes['ethnicity']}")
        
        if not updates:
            return ""
            
        return f"{'. '.join(updates)}."

    def add_human_touches(self, text: str, age_group: str) -> str:
        """Add human-like touches to the response based on age group."""
        if random.random() < 0.3:  # 30% chance to add casual expressions
            expressions = get_casual_expressions.invoke({"input": {"age_group": age_group}})
            if expressions and random.random() < 0.4:
                text = f"{random.choice(expressions)}, {text}"

        # Add occasional typos for younger age groups
        if age_group in ["teenager", "child"] and random.random() < 0.15:
            typos = [
                ("th", "ht"), ("er", "re"), ("you", "yuo"),
                ("with", "wiht"), ("what", "waht")
            ]
            for original, typo in typos:
                if original in text and random.random() < 0.2:
                    text = text.replace(original, typo, 1)

        return text

    def process_response(self, response: str, user_input: str, person_id: int, 
                        age: Optional[int], should_update_attributes: bool, 
                        attributes: Dict[str, str]) -> str:
        """Process and format the response with memory updates and human touches."""
        # Save the interaction in memory
        self.memory_manager.get_memory(person_id).chat_memory.add_message(HumanMessage(content=user_input))
        self.memory_manager.get_memory(person_id).chat_memory.add_message(AIMessage(content=response))
        
        # Add human touches based on age group
        age_group = determine_age_group.invoke({"input": {"age": age}})
        response = self.add_human_touches(response, age_group)
        
        return response 