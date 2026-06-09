import requests
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "kamekichi128/qwen3-4b-instruct-2507"

def _strip_thinking(text: str) -> str:
    text = text.strip()
    text = re.sub(r"(?is)^thinking\.\.\..*?\.\.\.done thinking\.\s*", "", text)
    text = re.sub(r"(?is)<think>.*?</think>", "", text)
    return text.strip()

def ask_ollama(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> str:
    full_prompt = prompt if not system else f"{system}\n\nUser:\n{prompt}"

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1200
            }
        },
        timeout=300
    )

    r.raise_for_status()
    data = r.json()

    return _strip_thinking(data.get("response", ""))