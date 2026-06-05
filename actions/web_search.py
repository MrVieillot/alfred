# web_search.py — Local mode / no Gemini
from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

from typing import Any


def _ddg_search(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS

    results = []

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            })

    return results


def _format_results(query: str, results: list[dict]) -> str:
    if not results:
        return f"No results found for: {query}"

    lines = [f"Search results for: {query}", ""]

    for i, r in enumerate(results, 1):
        title = r.get("title", "").strip()
        snippet = r.get("snippet", "").strip()
        url = r.get("url", "").strip()

        if title:
            lines.append(f"{i}. {title}")
        if snippet:
            lines.append(f"   {snippet}")
        if url:
            lines.append(f"   {url}")

        lines.append("")

    return "\n".join(lines).strip()


def _compare(items: list[str], aspect: str) -> str:
    aspect = aspect or "general"

    lines = [
        f"Comparison — {aspect.upper()}",
        "─" * 40,
    ]

    for item in items:
        query = f"{item} {aspect}"
        lines.append(f"\n▸ {item}")

        try:
            results = _ddg_search(query, max_results=3)

            if not results:
                lines.append("  No results found.")
                continue

            for r in results[:3]:
                snippet = r.get("snippet", "").strip()
                url = r.get("url", "").strip()

                if snippet:
                    lines.append(f"  • {snippet}")
                if url:
                    lines.append(f"    {url}")

        except Exception as e:
            lines.append(f"  Search failed: {e}")

    return "\n".join(lines).strip()


def web_search(
    parameters: dict | None,
    response: Any = None,
    player: Any = None,
    session_memory: Any = None,
) -> str:
    params = parameters or {}

    query = str(params.get("query", "") or "").strip()
    mode = str(params.get("mode", "search") or "search").lower().strip()
    items = params.get("items", [])
    aspect = str(params.get("aspect", "general") or "general").strip()

    if isinstance(items, str):
        items = [x.strip() for x in items.split(",") if x.strip()]

    if not query and not items:
        return "Please provide a search query, sir."

    if items and mode != "compare":
        mode = "compare"

    if player:
        try:
            player.write_log(f"[Search] {query or ', '.join(items)}")
        except Exception:
            pass

    print(f"[WebSearch] Query: {query!r} Mode: {mode}")
   

    try:
        if mode == "compare" and items:
            result = _compare(items, aspect)
        else:
            results = _ddg_search(query, max_results=6)
            for result in results[:3]:
                url = result.get("url", "")
                if url:
                    try:
                        webbrowser.open_new_tab(url)
                    except Exception as e:
                        print(f"[WebSearch] Open URL failed: {e}")

            result = _format_results(query, results)

        if session_memory:
            try:
                session_memory.set_last_search(
                    query=query or ", ".join(items),
                    response=result
                )
            except Exception:
                pass

        return result

    except Exception as e:
        print(f"[WebSearch] Search failed: {e}")
        return f"Search failed, sir: {e}"