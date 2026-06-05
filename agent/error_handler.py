import json
import re
import sys
from pathlib import Path
from enum import Enum


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"


class ErrorDecision(Enum):
    RETRY       = "retry"      
    SKIP        = "skip"       
    REPLAN      = "replan"     
    ABORT       = "abort"    


ERROR_ANALYST_PROMPT = """You are the error recovery module of MARK XXV AI assistant.

A task step has failed. Analyze the error and decide what to do.

DECISIONS:
- retry   : Transient error (network timeout, temporary file lock, race condition).
             The same step can succeed if tried again.
- skip    : This step is not critical and the task can succeed without it.
- replan  : The approach was wrong. A different tool or method should be tried.
- abort   : The task is fundamentally impossible or unsafe to continue.

Also provide:
- A brief explanation of WHY it failed (1 sentence)
- A fix suggestion if decision is replan (what to try instead)
- Max retries: how many times to retry if decision is retry (1 or 2)

Return ONLY valid JSON:
{
  "decision": "retry|skip|replan|abort",
  "reason": "why it failed",
  "fix_suggestion": "what to try instead (for replan)",
  "max_retries": 1,
  "user_message": "Short message to tell the user (max 15 words)"
}
"""


def analyze_error(
    step: dict,
    error: str,
    attempt: int = 1,
    max_attempts: int = 2
) -> dict:
    from agent.local_llm import ask_ollama

    if attempt >= max_attempts:
        print(f"[ErrorHandler] Max attempts reached for step {step.get('step')} — forcing replan")
        return {
            "decision": ErrorDecision.REPLAN,
            "reason": f"Failed {attempt} times: {error[:100]}",
            "fix_suggestion": "Try a completely different approach or tool",
            "max_retries": 0,
            "user_message": "Trying a different approach, sir."
        }

    prompt = f"""Failed step:
Tool: {step.get('tool')}
Description: {step.get('description')}
Parameters: {json.dumps(step.get('parameters', {}), indent=2)}
Critical: {step.get('critical', False)}

Error:
{error[:500]}

Attempt number: {attempt}"""

    try:
        text = ask_ollama(
            prompt=prompt,
            system=ERROR_ANALYST_PROMPT,
            model="qwen3.5:4b"
        )

        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        result = json.loads(text)

        decision_str = result.get("decision", "replan").lower()
        decision_map = {
            "retry": ErrorDecision.RETRY,
            "skip": ErrorDecision.SKIP,
            "replan": ErrorDecision.REPLAN,
            "abort": ErrorDecision.ABORT,
        }

        result["decision"] = decision_map.get(decision_str, ErrorDecision.REPLAN)

        if step.get("critical") and result["decision"] == ErrorDecision.SKIP:
            result["decision"] = ErrorDecision.REPLAN
            result["user_message"] = "This step is critical — finding alternative approach, sir."

        print(f"[ErrorHandler] Decision: {result['decision'].value} — {result.get('reason', '')}")
        return result

    except Exception as e:
        print(f"[ErrorHandler] Analysis failed: {e} — defaulting to replan")
        return {
            "decision": ErrorDecision.REPLAN,
            "reason": str(e),
            "fix_suggestion": "Try alternative approach",
            "max_retries": 1,
            "user_message": "Encountered an issue, adjusting approach, sir."
        }


def generate_fix(step: dict, error: str, fix_suggestion: str) -> dict:
    from agent.local_llm import ask_ollama

    prompt = f"""A task step failed. Generate a replacement step.

Original step:
Tool: {step.get('tool')}
Description: {step.get('description')}
Parameters: {json.dumps(step.get('parameters', {}), indent=2)}

Error:
{error[:300]}

Fix suggestion:
{fix_suggestion}

Return ONLY valid JSON for a replacement step using one of these tools:
web_search, browser_control, file_controller, computer_settings, computer_control, screen_process, send_message, reminder, desktop_control, youtube_video, weather_report, flight_finder, code_helper, dev_agent.

JSON format:
{{
  "step": {step.get("step")},
  "tool": "tool_name",
  "description": "replacement step description",
  "parameters": {{}},
  "depends_on": [],
  "critical": false
}}"""

    try:
        text = ask_ollama(
            prompt=prompt,
            system="You generate valid JSON replacement steps for MARK XXV. Return only JSON.",
            model="qwen3.5:4b"
        )

        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        new_step = json.loads(text)

        if "tool" not in new_step or "parameters" not in new_step:
            raise ValueError("Invalid replacement step structure")

        new_step.setdefault("step", step.get("step"))
        new_step.setdefault("description", f"Auto-fix for: {step.get('description')}")
        new_step.setdefault("depends_on", step.get("depends_on", []))
        new_step.setdefault("critical", step.get("critical", False))

        return new_step

    except Exception as e:
        print(f"[ErrorHandler] Fix generation failed: {e}")
        return {
            "step": step.get("step"),
            "tool": "code_helper",
            "description": f"Fallback for: {step.get('description')}",
            "parameters": {
                "action": "auto",
                "description": fix_suggestion or step.get("description", ""),
                "language": "python"
            },
            "depends_on": step.get("depends_on", []),
            "critical": step.get("critical", False)
        }