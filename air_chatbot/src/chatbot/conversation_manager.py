"""Conversation history management module for the chatbot."""
from typing import Dict, List, Optional
from datetime import datetime
from .database import get_database, Conversation

class ConversationManager:
    """Manages conversation history and summaries."""
    
    def __init__(self):
        """Initialize the conversation manager."""
        self.db = get_database()

    def get_past_conversations(self, person_id: int, limit: int = 5) -> List[Dict]:
        """Get recent conversation summaries for the person."""
        summaries = (
            self.db.query(Conversation)
            .filter(Conversation.person_id == person_id)
            .order_by(Conversation.end_time.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "summary": conv.summary,
                "start_time": conv.start_time,
                "end_time": conv.end_time
            }
            for conv in summaries
        ]

    def format_conversation_history(self, person_id: int) -> str:
        """Format recent conversations for context."""
        summaries = self.get_past_conversations(person_id)
        if not summaries:
            return "This is our first conversation."
            
        history = "Recent conversations:\n"
        for summary in summaries:
            history += f"Previous conversation ({summary['start_time'].strftime('%Y-%m-%d %H:%M')} to {summary['end_time'].strftime('%Y-%m-%d %H:%M')}):\n"
            history += f"Summary: {summary['summary']}\n"
        return history

    def get_conversation_history(self, person_id: Optional[int] = None) -> List[Dict]:
        """Get conversation history for a person."""
        if not person_id:
            return []
        return self.get_past_conversations(person_id)

    def add_conversation_summary(self, person_id: int, summary: str) -> bool:
        """Add a new conversation summary."""
        try:
            conversation = Conversation(
                person_id=person_id,
                summary=summary,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
            self.db.add(conversation)
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error adding conversation summary: {str(e)}")
            self.db.rollback()
            return False 