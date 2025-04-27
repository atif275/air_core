from typing import Optional
from langchain_openai import ChatOpenAI

class VisionManager:
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """Initialize the vision manager."""
        self.llm = llm

    def is_vision_query(self, user_input: str) -> bool:
        """
        Determine if the user's input requires visual analysis.
        Returns True if the query likely requires image analysis.
        """
        if not self.llm:
            return False
            
        # Create a prompt to analyze if the query requires visual capabilities
        vision_analysis_prompt = f"""
        Analyze if this query requires visual/image analysis capabilities to answer properly.
        Query: "{user_input}"
        
        Consider it a visual query if it:
        1. Asks about physical objects in view
        2. Requires seeing something to answer
        3. References visual elements like colors, numbers of items, or physical descriptions
        4. Asks about what is visible or what can be seen
        5. Requests information about images, photos, or visual content
        
        Respond with just 'true' or 'false'.
        """
        
        try:
            result = self.llm.predict(vision_analysis_prompt).lower().strip()
            return result == 'true'
        except Exception as e:
            print(f"Error analyzing vision query: {str(e)}")
            return False 