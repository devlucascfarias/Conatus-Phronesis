"""Curadoria via LLM-juiz (Fase 2, item 3) — o juiz é o Claude Code, sem API externa.

Fluxo:
    1. python src/judge_data.py prepare data/clean/dataset.jsonl
       → data/clean/to_judge.jsonl (um exemplo por linha, com índice)
    2. Claude Code lê to_judge.jsonl, aplica prompts/judge_system.md e escreve
       data/clean/verdicts.jsonl: {"i": n, "rationale_score": n, "tone_score": n,
       "verdict": "keep"|"discard", "reason": "..."}
    3. python src/judge_data.py apply data/clean/dataset.jsonl data/clean/verdicts.jsonl
       → data/clean/dataset_judged.jsonl (mantém só verdict == keep, notas >= 4)
"""
import argparse
import json
from pathlib import Path

from common import ROOT, read_jsonl

CLEAN_DIR = ROOT / "data" / "clean"


def prepare(dataset: Path) -> None:
    examples = read_jsonl(dataset)
    out = CLEAN_DIR / "to_judge.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for i, ex in enumerate(examples, 1):
            payload = {"i": i, "layer": ex.get("layer", ex.get("_task", {}).get("layer")), "messages": ex["messages"]}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"{len(examples)} exemplos → {out}. Claude Code julga com prompts/judge_system.md "
          f"e escreve data/clean/verdicts.jsonl.")


def apply(dataset: Path, verdicts_file: Path) -> None:
    examples = read_jsonl(dataset)
    verdicts = {v["i"]: v for v in read_jsonl(verdicts_file)}
    missing = [i for i in range(1, len(examples) + 1) if i not in verdicts]
    if missing:
        raise SystemExit(f"Faltam vereditos para os índices: {missing[:20]}{'…' if len(missing) > 20 else ''}")
    kept = [ex for i, ex in enumerate(examples, 1)
            if verdicts[i].get("verdict") == "keep"
            and verdicts[i].get("rationale_score", 0) >= 4
            and verdicts[i].get("tone_score", 0) >= 4]
    out = CLEAN_DIR / "dataset_judged.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for ex in kept:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Mantidos {len(kept)}/{len(examples)} → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["prepare", "apply"])
    ap.add_argument("dataset", type=Path)
    ap.add_argument("verdicts", type=Path, nargs="?")
    a = ap.parse_args()
    if a.mode == "prepare":
        prepare(a.dataset)
    else:
        if not a.verdicts:
            raise SystemExit("apply exige o arquivo de vereditos")
        apply(a.dataset, a.verdicts)
