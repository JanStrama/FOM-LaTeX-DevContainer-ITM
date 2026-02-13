#!/usr/bin/env python3
"""
Convert common chat export formats (JSON/JSONL) to Markdown.
Optionally render Markdown to PDF via pandoc (if available).

The script is intentionally tolerant and supports several simple shapes:
- JSONL: one JSON object per line
- JSON: list[object] or object with "messages"/"conversation" list

Expected message-like fields (best effort):
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
from typing import Iterable


ROLE_KEYS = ("role", "author", "speaker", "from")
TEXT_KEYS = ("text", "content", "message", "response", "output")


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", name.strip(), flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or "chat_export"


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


def normalize_messages(raw_messages: list[dict]) -> list[tuple[str, str]]:
    normalized: list[tuple[str, str]] = []
    for msg in raw_messages:
        role = pick_value(msg, ROLE_KEYS) or "unknown"
        text = pick_value(msg, TEXT_KEYS)
        if not text:
            # Some exports store the textual payload in nested fields.
            text = pick_value(msg, ("parts", "value", "body"))
        if not text:
            continue
        normalized.append((role, text))
    return normalized


def to_markdown(title: str, source_file: Path, messages: list[tuple[str, str]]) -> str:
    now = dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        f"# {title}",
        "",
        f"- Quelle: `{source_file.name}`",
        f"- Exportiert am: `{now}`",
        "",
        "---",
        "",
    ]
    for role, text in messages:
        lines.append(f"## {role}")
        lines.append("")
        lines.append(text.rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_pdf(md_path: Path, pdf_path: Path) -> None:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc not found in PATH")
    cmd = ["pandoc", str(md_path), "-o", str(pdf_path)]
    subprocess.run(cmd, check=True)


def process_file(input_path: Path, output_dir: Path, to_pdf: bool) -> tuple[Path, Path | None]:
    if input_path.suffix.lower() == ".jsonl":
        raw = read_jsonl(input_path)
    else:
        raw = read_json(input_path)

    messages = normalize_messages(raw)
    if not messages:
        raise ValueError(f"No parseable messages found in {input_path}")

    stem = sanitize_filename(input_path.stem)
    md_path = output_dir / f"{stem}.md"
    title = input_path.stem.replace("_", " ")
    md_text = to_markdown(title=title, source_file=input_path, messages=messages)
    md_path.write_text(md_text, encoding="utf-8")

    pdf_path: Path | None = None
    if to_pdf:
        pdf_path = output_dir / f"{stem}.pdf"
        write_pdf(md_path, pdf_path)

    return md_path, pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert chat exports to Markdown/PDF.")
    parser.add_argument("--input", required=True, help="Input JSON or JSONL file")
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

