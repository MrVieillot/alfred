import requests


OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen3.5:4b"

def ask_ollama(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> str:
    messages = []

    if system:
        messages.append({"role": "system", "content": system})

    messages.append({"role": "user", "content": prompt})

    r = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        },
        timeout=300
    )
    r.raise_for_status()
    
    return r.json()["message"]["content"].strip()