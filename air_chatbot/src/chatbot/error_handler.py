"""Error handling module for the chatbot."""
from typing import Any
from .logger import system_logger

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
        system_logger.log(error_msg, "ERROR")
        print(error_msg)
        
        if log_traceback:
            import traceback
            traceback_msg = f"Full traceback: {traceback.format_exc()}"
            system_logger.log(traceback_msg, "ERROR")
            print(traceback_msg)
            
        if should_raise:
            system_logger.log(f"Re-raising error in {context}", "ERROR")
            raise error
            
        system_logger.log(f"Returning fallback value for error in {context}", "INFO")
        return fallback_value

    @staticmethod
    def format_user_message(error: Exception) -> str:
        """Format an error message suitable for returning to users."""
        system_logger.log("Formatting user-friendly error message", "INFO")
        return "I apologize, but I encountered an issue. Please try again." 