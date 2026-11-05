"""LLM wrapper: provider switch in one place (anthropic | groq | openai), JSON mode, retries,
timeout and latency logging. With no API key the app runs in MOCK mode (no network calls).

Choose the provider with LLM_PROVIDER, or leave it empty: the first key found is used
(ANTHROPIC_API_KEY, then GROQ_API_KEY, then OPENAI_API_KEY)."""
import json
import os
import re
import time
import urllib.request

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")  # used for the anthropic provider
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))

# provider -> (key env var, model env var, default model, chat-completions URL)
_OPENAI_STYLE = {
    "groq": ("GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1/chat/completions"),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini", "https://api.openai.com/v1/chat/completions"),
}


def provider() -> str:
    p = os.getenv("LLM_PROVIDER", "").strip().lower()
    if p in ("anthropic", "groq", "openai"):
        return p
    for name, env in (("anthropic", "ANTHROPIC_API_KEY"), ("groq", "GROQ_API_KEY"), ("openai", "OPENAI_API_KEY")):
        if os.getenv(env):
            return name
    return "anthropic"


def is_mock() -> bool:
    p = provider()
    env = "ANTHROPIC_API_KEY" if p == "anthropic" else _OPENAI_STYLE[p][0]
    return not os.getenv(env)


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


def _complete(system: str, user: str, max_tokens: int) -> str:
    p = provider()
    if p == "anthropic":
        import anthropic

        client = anthropic.Anthropic(timeout=TIMEOUT)
        resp = client.messages.create(
            model=MODEL, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    key_env, model_env, default_model, url = _OPENAI_STYLE[p]
    body = json.dumps({
        "model": os.getenv(model_env, default_model), "max_tokens": max_tokens, "temperature": 0,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "User-Agent": "interviewlens/1.0",
        "Authorization": "Bearer " + os.environ[key_env]})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def call_json(system: str, user: str, max_tokens: int = 1500, retries: int = 2):
    """Call the LLM and return parsed JSON. Retries on bad JSON or a failed call."""
    last_err = None
    for _ in range(retries + 1):
        t0 = time.time()
        try:
            text = _complete(system + "\nReturn ONLY valid JSON. No prose, no markdown fences.", user, max_tokens)
            data = _extract_json(text)
            print(f"[llm] {provider()} ok in {int((time.time() - t0) * 1000)} ms")
            return data
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[llm] {provider()} failed after {int((time.time() - t0) * 1000)} ms: {e}")
    raise RuntimeError(f"LLM call failed: {last_err}")
