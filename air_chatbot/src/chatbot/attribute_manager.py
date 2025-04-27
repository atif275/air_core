"""Attribute management module for the chatbot."""
from typing import Dict, Literal, TypedDict
from .database import get_database, Person
from ..attributes_management.attributes_management import (
    identify_attributes,
    update_person_attributes
)

class AttributeDict(TypedDict):
    name: str
    age: str
    ethnicity: str
    confidence: Literal["high", "medium", "low"]

class AttributeManager:
    def __init__(self):
        self.db = get_database()

    def _identify_attributes(self, user_input: str) -> Dict[str, str]:
        """
        Identify if the user is trying to convey their name, age, or ethnicity.
        Returns a dictionary of identified attributes.
        """
        try:
            analysis_prompt = f"""
            Analyze this message and identify if the user is trying to convey their name, age, or ethnicity/location.
            Message: "{user_input}"
            
            Respond in valid JSON format with these fields (leave empty if not found):
            {{
                "name": "extracted name or empty string",
                "age": "extracted age (as string) or empty string",
                "ethnicity": "extracted ethnicity/location or empty string",
                "confidence": "high or medium or low"
            }}
            
            Examples of what to look for:
            - Name: "I am John", "My name is John", "Call me John", "This is John", etc.
            - Age: "I am 25", "I'm 25 years old", "25 years", etc.
            - Ethnicity/Location: Any mention of ethnicity, nationality, region, city, etc.
            
            Only extract information that is EXPLICITLY stated or very clearly implied.
            Set confidence to:
            - "high" if the information is explicitly stated
            - "medium" if it's strongly implied
            - "low" if it's weakly implied
            """
            
            result = identify_attributes.invoke({"input": {"user_input": user_input}})
            if not result:
                return {"name": "", "age": "", "ethnicity": "", "confidence": "low"}
                
            return result
            
        except Exception as e:
            print(f"Error in _identify_attributes: {str(e)}")
            return {"name": "", "age": "", "ethnicity": "", "confidence": "low"}

    def _update_person_attributes(self, person: Person, attributes: Dict[str, str]) -> bool:
        """
        Update the person's attributes in the database if they were identified with sufficient confidence.
        Returns True if any updates were made.
        """
        if not person or attributes["confidence"] == "low":
            return False

        try:
            updates = {}
            
            if attributes["name"] and attributes["confidence"] in ["high", "medium"]:
                updates["name"] = attributes["name"]
            
            if attributes["age"] and attributes["confidence"] in ["high"]:
                try:
                    age = int(attributes["age"])
                    if 0 <= age <= 150:
                        updates["age"] = age
                except ValueError:
                    pass
            
            if attributes["ethnicity"] and attributes["confidence"] in ["high", "medium"]:
                updates["ethnicity"] = attributes["ethnicity"]
            
            if updates:
                update_person_attributes.invoke({
                    "input": {
                        "person_id": person.id,
                        "attributes": updates
                    }
                })
                return True
                
        except Exception as e:
            print(f"Error in _update_person_attributes: {str(e)}")
            
        return False

    def process_attributes(self, user_input: str, person: Person) -> tuple[Dict[str, str], bool]:
        """
        Process attributes from user input and update if needed.
        Returns: (attributes_dict, was_updated)
        """
        attributes = self._identify_attributes(user_input)
        was_updated = self._update_person_attributes(person, attributes)
        return attributes, was_updated 