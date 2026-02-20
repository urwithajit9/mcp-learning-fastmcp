# research_server.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from fastmcp import FastMCP

mcp = FastMCP("ResearchAssistant 📚")

NOTES_DIR = Path("./research_notes")
NOTES_DIR.mkdir(exist_ok=True)


@mcp.tool
def save_note(title: str, content: str, tags: Optional[List[str]] = None) -> Dict:
    """
    Save a research note to a local file for later retrieval.
    Use this when the user wants to save, record, or remember information.
    Notes are saved with timestamps and can be tagged for organization.

    Args:
        title: Short title for the note (used as filename)
        content: The full content to save
        tags: Optional list of topic tags (e.g., ['AI', 'climate', 'research'])
    """
    note = {
        "title": title,
        "content": content,
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
    }

    # Sanitize filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    filename = NOTES_DIR / f"{safe_title}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(note, f, indent=2, ensure_ascii=False)

    return {
        "saved": True,
        "filename": str(filename),
        "title": title,
        "tags": note["tags"],
    }


@mcp.tool
def list_notes(tag: Optional[str] = None) -> Dict:
    """
    List all saved research notes, optionally filtered by tag.
    Use this when the user asks what notes they have, or wants to find notes on a topic.
    """
    notes = []
    for note_file in NOTES_DIR.glob("*.json"):
        try:
            with open(note_file, "r", encoding="utf-8") as f:
                note = json.load(f)
            if tag is None or tag.lower() in [t.lower() for t in note.get("tags", [])]:
                notes.append(
                    {
                        "title": note["title"],
                        "tags": note.get("tags", []),
                        "created_at": note.get("created_at"),
                        "filename": note_file.name,
                    }
                )
        except Exception:
            continue

    return {
        "notes": notes,
        "count": len(notes),
        "filter_tag": tag,
    }


@mcp.tool
def read_note(title: str) -> Dict:
    """
    Read the full content of a saved research note by its title.
    Use this when the user wants to recall, review, or read a specific note.
    """
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    filename = NOTES_DIR / f"{safe_title}.json"

    if not filename.exists():
        # Try partial match
        matches = list(NOTES_DIR.glob(f"*{safe_title[:10]}*.json"))
        if not matches:
            return {
                "error": f"Note '{title}' not found. Use list_notes to see available notes."
            }
        filename = matches[0]

    with open(filename, "r", encoding="utf-8") as f:
        note = json.load(f)

    return note


@mcp.tool
async def fetch_webpage_summary(url: str) -> Dict:
    """
    Fetch the content of a webpage and return its text content for analysis.
    Use this when the user wants to research a specific URL or webpage.
    Returns the raw text content (up to 5000 characters) for the LLM to summarize.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Research Bot)"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=headers, timeout=10, follow_redirects=True
            )

        # Very basic HTML stripping
        import re

        text = re.sub(r"<[^>]+>", " ", response.text)
        text = re.sub(r"\s+", " ", text).strip()

        return {
            "url": url,
            "status_code": response.status_code,
            "content_preview": text[:5000],
            "total_chars": len(text),
        }
    except Exception as e:
        return {"error": f"Failed to fetch {url}: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
