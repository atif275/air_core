"""Compatibility layer providing a minimal ConversationBufferMemory."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from langchain_core.chat_history import InMemoryChatMessageHistory, get_buffer_string
from langchain_core.messages import BaseMessage


@dataclass
class ConversationBufferMemory:
    """Lightweight drop-in replacement for the legacy LangChain memory class.

    The project relied on :class:`langchain.memory.ConversationBufferMemory`,
    which was removed in LangChain 0.2. This shim recreates the small subset
    of behaviour the codebase needs:
      * store chat history in memory
      * expose a ``chat_memory`` attribute with ``messages`` and ``add_*`` helpers
      * provide ``save_context`` and ``load_memory_variables`` utilities
    """

    return_messages: bool = True
    input_key: str = "input"
    output_key: str = "response"
    memory_key: str = "chat_history"
    _chat_memory: InMemoryChatMessageHistory = field(
        default_factory=InMemoryChatMessageHistory, init=False, repr=False
    )

    @property
    def chat_memory(self) -> InMemoryChatMessageHistory:
        return self._chat_memory

    def clear(self) -> None:
        self._chat_memory = InMemoryChatMessageHistory()

    # Legacy API compatibility -------------------------------------------------
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """Persist a single conversational turn."""
        user_input = self._extract_text(inputs, self.input_key)
        ai_output = self._extract_text(outputs, self.output_key)
        if user_input:
            self._chat_memory.add_user_message(user_input)
        if ai_output:
            self._chat_memory.add_ai_message(ai_output)

    def load_memory_variables(self, _: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the stored history in either message or string form."""
        if self.return_messages:
            return {self.memory_key: list(self._chat_memory.messages)}
        return {self.memory_key: get_buffer_string(self._chat_memory.messages)}

    # Utility methods ---------------------------------------------------------
    @staticmethod
    def _extract_text(data: Dict[str, Any], preferred_key: str) -> str:
        if preferred_key in data and data[preferred_key] is not None:
            return str(data[preferred_key])
        if "content" in data and data["content"] is not None:
            return str(data["content"])
        for value in data.values():
            if value is not None:
                return str(value)
        return ""

    # Convenience pass-throughs ------------------------------------------------
    def add_message(self, message: BaseMessage) -> None:
        self._chat_memory.add_message(message)

    def __iter__(self) -> Iterable[BaseMessage]:
        return iter(self._chat_memory.messages)


