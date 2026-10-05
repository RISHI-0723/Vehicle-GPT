"""Conversation history bounding.

An "exchange" is one user message plus one assistant message. The AI
service retains at most 6 exchanges (12 messages) of history; anything
older is discarded. The system prompt is never part of this list and is
never counted as an exchange.
"""
from typing import List

from app.ai.schemas import ConversationMessage

MAX_EXCHANGES = 6
MAX_MESSAGES = MAX_EXCHANGES * 2


def bound_conversation(messages: List[ConversationMessage]) -> List[ConversationMessage]:
    """Keep only the most recent MAX_MESSAGES entries, oldest discarded first."""
    if len(messages) <= MAX_MESSAGES:
        return list(messages)
    return list(messages[-MAX_MESSAGES:])
