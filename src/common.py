"""Utilitários compartilhados do pipeline."""
import json
import re
import sys
from pathlib import Path

import yaml

# Console do Windows (cp1252) derruba print() com acentos/setas; força UTF-8 na saída.
# Linux/Colab já usam UTF-8 por padrão, então isto é um no-op lá.
for _stream in (sys.stdout, sys.stderr):
    if getattr(_stream, "encoding", "").lower() != "utf-8":
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

ROOT = Path(__file__).resolve().parents[1]

TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def load_yaml(rel_path: str) -> dict:
    with open(ROOT / rel_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_tools() -> list[dict]:
    with open(ROOT / "configs" / "tools.json", encoding="utf-8") as f:
        return json.load(f)["tools"]


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_tool_calls(text: str) -> list[dict]:
    """Extrai os JSONs de <tool_call> de um turno do assistant. JSON inválido vira {'_invalid': raw}."""
    calls = []
    for raw in TOOL_CALL_RE.findall(text or ""):
        try:
            calls.append(json.loads(raw))
        except json.JSONDecodeError:
            calls.append({"_invalid": raw})
    return calls


def preamble_text(assistant_content: str) -> str:
    """Texto antes da primeira tool call; se não houver tool call, o primeiro parágrafo."""
    m = TOOL_CALL_RE.search(assistant_content or "")
    if m:
        return assistant_content[: m.start()].strip()
    return (assistant_content or "").strip().split("\n\n")[0].strip()


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])
