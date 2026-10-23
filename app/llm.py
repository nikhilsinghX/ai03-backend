"""LLM wrapper. Real Claude call if ANTHROPIC_API_KEY is set, else MOCK mode.
Member 2 only needs to edit the prompts in pipeline.py, not this file."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")


def is_mock() -> bool:
    return not os.getenv("ANTHROPIC_API_KEY")


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise


def call_json(system: str, user: str, max_tokens: int = 1500, retries: int = 2):
    """Call the LLM and return parsed JSON. Retries on bad JSON."""
    import anthropic

    client = anthropic.Anthropic()
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system + "\nReturn ONLY valid JSON. No prose, no markdown fences.",
                messages=[{"role": "user", "content": user}],
            )
            return _extract_json(resp.content[0].text)
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise RuntimeError(f"LLM call failed: {last_err}")
