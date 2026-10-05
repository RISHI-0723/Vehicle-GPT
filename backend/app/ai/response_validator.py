"""Validates raw Ollama output before it is ever returned to a client.

The model is instructed to reply with {"answer": "<text>"} and nothing else
(see system_prompt.py). Evidence, actions, confidence, and intent are never
parsed from the model's output -- they are always the backend-computed
values, so they cannot be invented, upgraded, or substituted by the model.
This function's only job is to validate that "answer" is usable text.
Anything else -- invalid JSON, a missing/empty/non-string answer, or a
suspiciously huge payload -- is rejected so the caller falls back to the
deterministic formatter instead of crashing or leaking a malformed reply.
"""
import json

MAX_ANSWER_LENGTH = 4000


class InvalidOllamaOutput(Exception):
    """Raised when the model's output cannot be trusted as-is."""


def validate_ollama_answer(raw: str) -> str:
    """Parse and validate raw Ollama content, returning a clean answer string.

    Raises InvalidOllamaOutput for anything that doesn't match the required shape.
    """
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise InvalidOllamaOutput("Model output was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise InvalidOllamaOutput("Model output was not a JSON object")

    answer = parsed.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise InvalidOllamaOutput("Model output was missing a non-empty 'answer' string")

    if len(answer) > MAX_ANSWER_LENGTH:
        raise InvalidOllamaOutput("Model output exceeded the maximum answer length")

    return answer.strip()
