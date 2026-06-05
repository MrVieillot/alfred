import json
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR    = get_base_dir()
CONFIG_DIR  = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"

def _detect_os() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"

def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def config_exists() -> bool:
    return CONFIG_FILE.exists()

def save_api_keys(gemini_api_key: str = "local_mode") -> None:
    """Compatibility function.

    The original project required a Gemini API key.
    In local/Ollama mode, we keep a harmless placeholder so older UI code
    that reads config/api_keys.json does not block startup.
    """
    ensure_config_dir()

    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    data["gemini_api_key"] = gemini_api_key.strip() or "local_mode"
    data.setdefault("os_system", _detect_os())
    data["llm_provider"] = "ollama"

    CONFIG_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )

def load_api_keys() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to load api_keys.json: {e}")
        return {}

def get_gemini_key() -> str | None:
    # Kept for backward compatibility with old code paths.
    return load_api_keys().get("gemini_api_key", "local_mode")

def ensure_local_config() -> dict:
    """Create a valid local-mode config if it does not exist."""
    ensure_config_dir()
    data = load_api_keys()
    changed = False

    if not data.get("gemini_api_key"):
        data["gemini_api_key"] = "local_mode"
        changed = True

    if not data.get("os_system"):
        data["os_system"] = _detect_os()
        changed = True

    if data.get("llm_provider") != "ollama":
        data["llm_provider"] = "ollama"
        changed = True

    if changed:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return data

def is_configured() -> bool:
    ensure_local_config()
    return True