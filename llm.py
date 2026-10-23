

import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL")

if not api_key or not model:
    raise RuntimeError(
        "Set GROQ_API_KEY and GROQ_MODEL in your .env file"
    )

client = Groq(api_key=api_key)


def generate_json(system_prompt: str, user_prompt: str) -> dict:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("The AI returned an empty response")

    return json.loads(content)
