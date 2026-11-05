"""Compatibility adapter: Member 2 expects generate_json; Member 1 exposes call_json."""
from ..llm import call_json

def generate_json(system_prompt: str, user_prompt: str) -> dict:
    return call_json(system_prompt, user_prompt)
