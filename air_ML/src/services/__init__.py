from src.conversation.memory import chat_memory
from .memory_service import MemoryService

memory_service = MemoryService(chat_memory)

__all__ = ['memory_service'] 