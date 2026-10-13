"""Shared plumbing for the three sublabs: one client, one model, JSON parsing.

Nothing interesting lives here on purpose - the prompts, the state and the
rules are in the sublab modules.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUTPUTS = ROOT / "outputs"

load_dotenv(ROOT / ".env")

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

# Windows consoles default to cp1251/cp866 and choke on Kazakh letters.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

_client = None


def client():
    global _client
    if _client is None:
        if not os.getenv("OPENAI_API_KEY"):
            sys.exit("OPENAI_API_KEY is not set. Copy .env.example to .env and put your key in it.")
        from openai import OpenAI

        _client = OpenAI()
    return _client


def load_json(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def chat(messages: list[dict], json_mode: bool = True, retries: int = 2) -> tuple[str, dict]:
    """One stateless call. Returns (reply text, usage dict)."""
    kwargs = {"model": MODEL, "messages": messages}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    for attempt in range(retries + 1):
        try:
            resp = client().chat.completions.create(**kwargs)
            break
        except Exception as exc:  # network blips, rate limits
            if attempt == retries:
                raise
            print(f"  [retry {attempt + 1} after error: {exc}]", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    usage = resp.usage
    return resp.choices[0].message.content or "", {
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json(text: str):
    """Parse a reply as a JSON object. Returns None if it is not one.

    Code fences are tolerated because a fence is formatting, not content;
    anything else that is not a JSON object counts as a parse failure.
    """
    try:
        obj = json.loads(_FENCE.sub("", text.strip()))
    except (json.JSONDecodeError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def count_tokens(messages: list[dict]) -> int:
    """Local estimate of what a message list costs, for when no call was made."""
    import tiktoken

    enc = tiktoken.get_encoding("o200k_base")
    return sum(len(enc.encode(m["content"])) + 4 for m in messages) + 2


def save_output(name: str, obj) -> Path:
    OUTPUTS.mkdir(exist_ok=True)
    path = OUTPUTS / name
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def md_table(header: list[str], rows: list[list]) -> str:
    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)
