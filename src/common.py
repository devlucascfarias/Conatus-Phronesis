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
THINK_BLOCK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
THINK_TAG_RE = re.compile(r"</?think>")
THINK_TURN_RE = re.compile(
    r"\A<think>\n(?P<reasoning>.*?)\n</think>(?:\n\n(?P<visible>.*))?\Z",
    re.DOTALL,
)


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


def think_format_error(assistant_content: str) -> str | None:
    """Valida o bloco de reasoning embutido no início de um turno assistant."""
    text = assistant_content or ""
    if not THINK_TAG_RE.search(text):
        return None
    match = THINK_TURN_RE.fullmatch(text)
    if not match:
        return "bloco_think_malformado"
    reasoning = match.group("reasoning")
    if not reasoning.strip():
        return "bloco_think_vazio"
    if THINK_TAG_RE.search(reasoning):
        return "bloco_think_malformado"
    if "<tool_call>" in reasoning or "</tool_call>" in reasoning:
        return "tool_call_dentro_do_think"
    return None


def think_text(assistant_content: str) -> str:
    """Retorna o conteúdo do bloco <think> de um turno (string vazia se não houver ou malformado)."""
    match = THINK_TURN_RE.fullmatch(assistant_content or "")
    return match.group("reasoning").strip() if match else ""


def strip_think_blocks(text: str) -> str:
    """Remove reasoning oculto antes de métricas sobre a resposta visível."""
    visible = THINK_BLOCK_RE.sub("", text or "")
    # Geração truncada pode terminar antes de </think>; isso não é preâmbulo visível.
    return re.sub(r"<think>.*\Z", "", visible, flags=re.DOTALL)


def preamble_text(assistant_content: str) -> str:
    """Preâmbulo visível antes da tool call, sem contar blocos de reasoning."""
    visible = strip_think_blocks(assistant_content)
    m = TOOL_CALL_RE.search(visible)
    if m:
        return visible[: m.start()].strip()
    return visible.strip().split("\n\n")[0].strip()


def word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])
