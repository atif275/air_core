import json
from typing import Dict, Optional, List
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from ..database.database import get_database, Person
import os
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

# Initialize OpenAI client
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)

class IdentifyAttributesInput(BaseModel):
    user_input: str

class UpdatePersonAttributesInput(BaseModel):
    person_id: int
    attributes: Dict[str, str]

class DetermineAgeGroupInput(BaseModel):
    age: int

class GetCasualExpressionsInput(BaseModel):
    age_group: str

@tool
def identify_attributes(input: IdentifyAttributesInput) -> Dict[str, str]:
    """
    Identify if the user is trying to convey their name, age, ethnicity, or language.
    
    Args:
        input: IdentifyAttributesInput containing user_input to analyze
        
    Returns:
        Dict containing identified attributes (name, age, ethnicity, language) and confidence level
    """
    analysis_prompt = f"""
    Analyze this message and identify if the user is trying to convey their name, age, ethnicity/location, or language.
    Message: "{input.user_input}"
    
    Respond in valid JSON format with these fields (leave empty if not found):
    {{
        "name": "extracted name or empty string",
        "age": "extracted age (as string) or empty string",
        "ethnicity": "extracted ethnicity/location or empty string",
        "language": "extracted language or empty string",
        "confidence": "high or medium or low"
    }}
    
    Examples of what to look for:
    - Name: "I am John", "My name is John", "Call me John", "This is John", etc.
    - Age: "I am 25", "I'm 25 years old", "25 years", etc.
    - Ethnicity/Location: Any mention of ethnicity, nationality, region, city, etc.
    - Language: Any mention of languages like "I speak English", "Roman Urdu", "Spanish", etc.
    
    Important rules:
    1. Only extract information that is EXPLICITLY stated or very clearly implied
    2. Do NOT interpret languages as ethnicities/locations
    3. For language detection, look for phrases like:
       - "I speak [language]"
       - "I know [language]"
       - "I can speak [language]"
       - "My language is [language]"
    4. Set confidence to:
       - "high" if the information is explicitly stated
       - "medium" if it's strongly implied
       - "low" if it's weakly implied
    """
    
    try:
        result = llm.predict(analysis_prompt)
        attributes = json.loads(result)
        return attributes
    except Exception as e:
        print(f"Error analyzing attributes: {str(e)}")
        return {"name": "", "age": "", "ethnicity": "", "language": "", "confidence": "low"}

@tool
def update_person_attributes(input: UpdatePersonAttributesInput) -> bool:
    """
    Update the person's attributes in the database if they were identified with sufficient confidence.
    
    Args:
        input: UpdatePersonAttributesInput containing person_id and attributes
        
    Returns:
        bool: True if any updates were made, False otherwise
    """
    if input.attributes["confidence"] == "low":
        return False

    db = get_database()
    try:
        updates = {}
        
        # Only update attributes that are present and have sufficient confidence
        if input.attributes["name"] and input.attributes["confidence"] in ["high", "medium"]:
            updates["name"] = input.attributes["name"]
        
        if input.attributes["age"] and input.attributes["confidence"] in ["high"]:
            try:
                age = int(input.attributes["age"])
                if 0 <= age <= 150:  # Basic age validation
                    updates["age"] = age
            except ValueError:
                pass
        
        if input.attributes["ethnicity"] and input.attributes["confidence"] in ["high", "medium"]:
            updates["ethnicity"] = input.attributes["ethnicity"]
            
        if input.attributes["language"] and input.attributes["confidence"] in ["high", "medium"]:
            updates["language"] = input.attributes["language"]
        
        # If we have updates to make
        if updates:
            # Update the database
            db.query(Person).filter(Person.id == input.person_id).update(updates)
            db.commit()
            return True
                
    except Exception as e:
        print(f"Error updating person attributes: {str(e)}")
        db.rollback()
    
    return False

@tool
def determine_age_group(input: DetermineAgeGroupInput) -> str:
    """
    Determine the age group of a person based on their age.
    
    Args:
        input: DetermineAgeGroupInput containing age
        
    Returns:
        str: The age group category (child, teenager, adult, or senior)
    """
    if input.age <= 12:
        return "child"
    elif input.age <= 19:
        return "teenager"
    elif input.age <= 65:
        return "adult"
    else:
        return "senior"