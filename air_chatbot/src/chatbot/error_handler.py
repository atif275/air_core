"""Error handling module for the chatbot."""
from typing import Any

class ErrorHandler:
    """Centralized error handling for the chatbot."""
    
    @staticmethod
    def handle_error(error: Exception, context: str, fallback_value: Any = None, 
                    log_traceback: bool = False, should_raise: bool = False) -> Any:
        """
        Handle errors in a consistent way across the chatbot.
        
        Args:
            error: The exception that was caught
            context: Description of where the error occurred
            fallback_value: Value to return if not raising the error
            log_traceback: Whether to log the full traceback
            should_raise: Whether to re-raise the exception
            
        Returns:
            fallback_value if not raising, otherwise raises the exception
        """
        error_msg = f"Error in {context}: {str(error)}"
        print(error_msg)
        
        if log_traceback:
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            
        if should_raise:
            raise error
            
        return fallback_value

    @staticmethod
    def format_user_message(error: Exception) -> str:
        """Format an error message suitable for returning to users."""
        return "I apologize, but I encountered an issue. Please try again." 