#!/usr/bin/env python3
"""
Convert chat export formats to Markdown.
Optionally render Markdown to PDF via pandoc (if available).

Supported input formats (auto-detected by file extension):
- .md   : Opencode recorded sessions (Markdown with embedded tool calls)
- .jsonl: One JSON object per line (Claude Code JSONL export)
- .json : list[object] or object with "messages"/"conversation" list

Expected message-like fields for JSON/JSONL (best effort):
- role: role/author/speaker/from
- text: text/content/message/response/output
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, NamedTuple


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

class Message(NamedTuple):
    role: str
    text: str


class SessionMeta(NamedTuple):
    title: str
    session_id: str | None
    created: str | None
    updated: str | None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

ROLE_KEYS = ("role", "author", "speaker", "from")
TEXT_KEYS = ("text", "content", "message", "response", "output")

# Opencode assistant header: "## Assistant (Plan · model · 2.4s)"
_ASSISTANT_HEADER_RE = re.compile(r"^Assistant\s*\(.*?\)\s*$", re.IGNORECASE)

# Bold markers used in Opencode tool blocks
_TOOL_MARKER_RE = re.compile(r"^\*\*Tool:\s")
_INPUT_MARKER_RE = re.compile(r"^\*\*Input:\*\*\s*$")
_OUTPUT_MARKER_RE = re.compile(r"^\*\*Output:\*\*\s*$")
_FENCE_RE = re.compile(r"^```")


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", name.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or "chat_export"


# ---------------------------------------------------------------------------
# JSON / JSONL readers
# ---------------------------------------------------------------------------

def read_jsonl(path: Path) -> list[dict]:
    messages: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                messages.append(obj)
    return messages


def read_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)

    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]

    if isinstance(obj, dict):
        for key in ("messages", "conversation", "chat", "items"):
            val = obj.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        return [obj]

    return []


def pick_value(payload: dict, keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            nested = pick_value(value, keys)
            if nested:
                return nested
        if isinstance(value, list):
            chunks: list[str] = []
            for item in value:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    nested = pick_value(item, keys)
                    if nested:
                        chunks.append(nested)
            if chunks:
                return "\n".join(chunks).strip()
    return None


def normalize_json_messages(raw_messages: list[dict]) -> list[Message]:
    normalized: list[Message] = []
    for msg in raw_messages:
        role = pick_value(msg, ROLE_KEYS) or "unknown"
        text = pick_value(msg, TEXT_KEYS)
        if not text:
            text = pick_value(msg, ("parts", "value", "body"))
        if not text:
            continue
        normalized.append(Message(role=role, text=text))
    return normalized


def parse_json_session(path: Path) -> tuple[SessionMeta, list[Message]]:
    if path.suffix.lower() == ".jsonl":
        raw = read_jsonl(path)
    else:
        raw = read_json(path)
    messages = normalize_json_messages(raw)
    meta = SessionMeta(
        title=path.stem.replace("_", " "),
        session_id=None,
        created=None,
        updated=None,
    )
    return meta, messages


# ---------------------------------------------------------------------------
# Opencode Markdown session reader
# ---------------------------------------------------------------------------

def _strip_tool_calls(text: str) -> str:
    """Remove embedded tool-call blocks from an assistant message.

    Opencode embeds tool calls like:

        **Tool: <name>**

        **Input:**
        ```json
        { ... }
        ```

        **Output:**
        ```
        ... (may itself contain ``` fences) ...
        ```

    The tricky part is that Output blocks can contain nested fenced code.
    We use a line-based state machine:

    - STATE prose   : emit lines; switch to tool_header on **Tool:**
    - STATE tool_header: discard; switch to fence_wait on **Input:**/**Output:**
                         or back to prose on any other non-blank line
    - STATE fence_wait: discard; switch to in_fence on ```
                        or back to tool_header on **Input:**/**Output:**
    - STATE in_fence: count fence depth (nested ``` pairs); when depth 0
                      return to tool_header (more Input/Output may follow)
    """
    STATE_PROSE = "prose"
    STATE_TOOL = "tool"       # inside a tool block, between fences
    STATE_FENCE_WAIT = "fence_wait"  # just saw Input/Output label
    STATE_IN_FENCE = "in_fence"      # inside a ``` ... ``` block

    state = STATE_PROSE
    fence_depth = 0
    result: list[str] = []

    for line in text.splitlines():
        if state == STATE_PROSE:
            if _TOOL_MARKER_RE.match(line):
                state = STATE_TOOL
                # discard the **Tool: ...** line
            else:
                result.append(line)

        elif state == STATE_TOOL:
            # Discard everything; watch for Input/Output labels and new Tool
            if _INPUT_MARKER_RE.match(line) or _OUTPUT_MARKER_RE.match(line):
                state = STATE_FENCE_WAIT
            elif _TOOL_MARKER_RE.match(line):
                pass  # another tool call; stay in tool state
            elif line.strip() == "":
                pass  # blank line inside tool block
            else:
                # Non-label, non-blank, non-fence -> back to prose
                state = STATE_PROSE
                result.append(line)

        elif state == STATE_FENCE_WAIT:
            # Expect a ``` opening fence next (possibly after blank lines)
            if _FENCE_RE.match(line):
                state = STATE_IN_FENCE
                fence_depth = 1
            elif _INPUT_MARKER_RE.match(line) or _OUTPUT_MARKER_RE.match(line):
                pass  # another label, stay waiting
            elif line.strip() == "":
                pass  # blank line between label and fence
            else:
                # Unexpected content; treat as non-fenced output, discard
                pass

        elif state == STATE_IN_FENCE:
            if _FENCE_RE.match(line):
                fence_depth -= 1
                if fence_depth <= 0:
                    # Fence closed — return to tool state (more Input/Output may follow)
                    state = STATE_TOOL
                    fence_depth = 0
                # else: still inside nested fence (rare edge case), discard
            else:
                # Content inside fence — discard

                pass

    cleaned = "\n".join(result)
    # Collapse runs of blank lines left behind
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _normalize_role(raw_header: str) -> str:
    """Convert Opencode section headers to a clean role label.

    '## User'                          -> 'User'
    '## Assistant (Plan · model · t)'  -> 'Assistant'
    """
    header = raw_header.lstrip("#").strip()
    if _ASSISTANT_HEADER_RE.match(header):
        return "Assistant"
    return header


def parse_opencode_session(path: Path) -> tuple[SessionMeta, list[Message]]:
    """Parse an Opencode-generated Markdown session file.

    Structure expected:
        # Title
        **Session ID:** <id>
        **Created:** <ts>
        **Updated:** <ts>
        ---
        ## User
        <text>
        ---
        ## Assistant (Plan · model · time)
        <text with optional tool blocks>
        ---
        ...
    """
    raw = path.read_text(encoding="utf-8")

    # --- Extract title and metadata from the preamble ----------------------
    title = path.stem.replace("_", " ")
    session_id: str | None = None
    created: str | None = None
    updated: str | None = None

    title_m = re.match(r"^#\s+(.+)", raw)
    if title_m:
        title = title_m.group(1).strip()

    for label, attr in (
        ("Session ID", "session_id"),
        ("Created", "created"),
        ("Updated", "updated"),
    ):
        m = re.search(rf"\*\*{label}:\*\*\s*(.+)", raw)
        if m:
            if attr == "session_id":
                session_id = m.group(1).strip()
            elif attr == "created":
                created = m.group(1).strip()
            else:
                updated = m.group(1).strip()

    meta = SessionMeta(
        title=title,
        session_id=session_id,
        created=created,
        updated=updated,
    )

    # --- Split into message sections at "## <Role ...>" headers -------------
    # We split on lines that start with "## " (level-2 headings used as roles)
    section_re = re.compile(r"^(#{2}\s+.+)$", re.MULTILINE)
    parts = section_re.split(raw)
    # parts alternates: [preamble, header1, body1, header2, body2, ...]

    messages: list[Message] = []
    # Iterate header/body pairs (skip index 0 which is the preamble)
    i = 1
    while i < len(parts) - 1:
        raw_header = parts[i].strip()
        body = parts[i + 1]
        i += 2

        role = _normalize_role(raw_header)

        # Remove leading/trailing horizontal rules used as separators
        body = re.sub(r"^\s*---\s*$", "", body, flags=re.MULTILINE)

        if role == "Assistant":
            body = _strip_tool_calls(body)

        body = body.strip()
        # Skip tool-only assistant turns that left no prose
        if body:
            messages.append(Message(role=role, text=body))

    return meta, messages


# ---------------------------------------------------------------------------
# Markdown renderer
# ---------------------------------------------------------------------------

def to_markdown(
    meta: SessionMeta,
    source_file: Path,
    messages: list[Message],
) -> str:
    now = dt.datetime.now().isoformat(timespec="seconds")
    lines: list[str] = [
        f"# {meta.title}",
        "",
        f"- Quelle: `{source_file.name}`",
        f"- Exportiert am: `{now}`",
    ]

    if meta.session_id:
        lines.append(f"- Session ID: `{meta.session_id}`")
    if meta.created:
        lines.append(f"- Erstellt: `{meta.created}`")
    if meta.updated:
        lines.append(f"- Aktualisiert: `{meta.updated}`")

    lines += ["", "---", ""]

    for msg in messages:
        lines.append(f"## {msg.role}")
        lines.append("")
        lines.append(msg.text.rstrip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

def write_pdf(md_path: Path, pdf_path: Path) -> None:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found in PATH")
    cmd = ["pandoc", str(md_path), "-o", str(pdf_path)]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Top-level processing
# ---------------------------------------------------------------------------

def _detect_format(path: Path) -> str:
    """Return 'opencode', 'jsonl', or 'json' based on file extension."""
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "opencode"
    if suffix == ".jsonl":
        return "jsonl"
    return "json"


def process_file(
    input_path: Path,
    output_dir: Path,
    to_pdf: bool,
) -> tuple[Path, Path | None]:
    fmt = _detect_format(input_path)

    if fmt == "opencode":
        meta, messages = parse_opencode_session(input_path)
    else:
        meta, messages = parse_json_session(input_path)

    if not messages:
        raise ValueError(f"No parseable messages found in {input_path}")

    stem = sanitize_filename(input_path.stem)
    md_path = output_dir / f"{stem}.md"
    md_text = to_markdown(meta=meta, source_file=input_path, messages=messages)
    md_path.write_text(md_text, encoding="utf-8")

    pdf_path: Path | None = None
    if to_pdf:
        pdf_path = output_dir / f"{stem}.pdf"
        write_pdf(md_path, pdf_path)

    return md_path, pdf_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert chat exports (JSON, JSONL, Opencode Markdown) to Markdown/PDF."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input file: .md (Opencode session), .json, or .jsonl",
    )
    parser.add_argument(
        "--output",
        default="literatur/fluechtige_quellen/ki_chats",
        help="Output directory for generated files",
    )
    parser.add_argument(
        "--to-pdf",
        action="store_true",
        help="Also render PDF via pandoc",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        md_path, pdf_path = process_file(input_path, output_dir, args.to_pdf)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"OK: Markdown written to {md_path}")
    if pdf_path is not None:
        print(f"OK: PDF written to {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
