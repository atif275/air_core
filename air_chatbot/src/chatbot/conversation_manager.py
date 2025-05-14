"""Conversation history management module for the chatbot."""
from typing import Dict, List, Optional
from datetime import datetime
from ..database.database import get_database, Conversation
from .logger import system_logger

class ConversationManager:
    """Manages conversation history and summaries."""
    
    def __init__(self):
        """Initialize the conversation manager."""
        system_logger.log("Initializing ConversationManager")
        self.db = get_database()
        system_logger.log("Database connection established")

    def get_past_conversations(self, person_id: int, limit: int = 5) -> List[Dict]:
        """Get recent conversation summaries for the person."""
        system_logger.log(f"Getting past conversations for person_id: {person_id}, limit: {limit}")
        try:
            summaries = (
                self.db.query(Conversation)
                .filter(Conversation.person_id == person_id)
                .order_by(Conversation.end_time.desc())
                .limit(limit)
                .all()
            )
            system_logger.log(f"Retrieved {len(summaries)} past conversations")
            return [
                {
                    "summary": conv.summary,
                    "start_time": conv.start_time,
                    "end_time": conv.end_time
                }
                for conv in summaries
            ]
        except Exception as e:
            system_logger.log(f"Error retrieving past conversations: {str(e)}", "ERROR")
            return []

    def format_conversation_history(self, person_id: int) -> str:
        """Format recent conversations for context."""
        system_logger.log(f"Formatting conversation history for person_id: {person_id}")
        summaries = self.get_past_conversations(person_id)
        if not summaries:
            system_logger.log("No past conversations found")
            return "This is our first conversation."
            
        history = "Recent conversations:\n"
        for summary in summaries:
            history += f"Previous conversation ({summary['start_time'].strftime('%Y-%m-%d %H:%M')} to {summary['end_time'].strftime('%Y-%m-%d %H:%M')}):\n"
            history += f"Summary: {summary['summary']}\n"
        system_logger.log(f"Formatted {len(summaries)} conversations into history")
        return history

    def get_conversation_history(self, person_id: Optional[int] = None) -> List[Dict]:
        """Get conversation history for a person."""
        if not person_id:
            system_logger.log("No person_id provided for conversation history", "WARNING")
            return []
        system_logger.log(f"Getting conversation history for person_id: {person_id}")
        return self.get_past_conversations(person_id)

    def add_conversation_summary(self, person_id: int, summary: str) -> bool:
        """Add a new conversation summary."""
        system_logger.log(f"Adding conversation summary for person_id: {person_id}")
        try:
            conversation = Conversation(
                person_id=person_id,
                summary=summary,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
            self.db.add(conversation)
            self.db.commit()
            system_logger.log("Successfully added conversation summary")
            return True
        except Exception as e:
            error_msg = f"Error adding conversation summary: {str(e)}"
            system_logger.log(error_msg, "ERROR")
            print(error_msg)  # Keep existing print for backward compatibility
            self.db.rollback()
            return False 