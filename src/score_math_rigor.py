"""Curadoria do held-out de rigor matemático via LLM-juiz — mesmo padrão de
src/judge_data.py: "o juiz é o Claude Code, sem API externa" (comparação
simbólica de LaTeX é frágil demais pra um comparador mecânico — vetores,
matrizes, respostas de prova sem \\boxed{} não dão pra normalizar por string).

Fluxo:
    1. python src/run_math_rigor_eval.py --model ... --adapter ...  (Colab, GPU)
       → outputs/math_rigor_responses.jsonl
    2. python src/score_math_rigor.py prepare outputs/math_rigor_responses.jsonl
       → outputs/math_rigor_to_judge.jsonl (um par pergunta/referência/resposta por linha)
    3. Claude Code lê to_judge.jsonl, aplica prompts/judge_math_rigor.md e escreve
       outputs/math_rigor_verdicts.jsonl: {"i": n, "verdict": "...", "reason": "..."}
    4. python src/score_math_rigor.py apply outputs/math_rigor_responses.jsonl outputs/math_rigor_verdicts.jsonl
       → relatório agregado (accuracy por família, por veredito)
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from common import ROOT, read_jsonl

OUT_DIR = ROOT / "outputs"
VERDICTS = ("correct", "partially_correct", "incorrect", "incomplete")


def prepare(responses_file: Path) -> None:
    rows = read_jsonl(responses_file)
    out = OUT_DIR / "math_rigor_to_judge.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            payload = {"i": r["i"], "question": r["question"], "reference": r["reference"], "response": r["response"]}
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    print(f"{len(rows)} pares → {out}. Claude Code julga com prompts/judge_math_rigor.md "
          f"e escreve outputs/math_rigor_verdicts.jsonl.")


def apply(responses_file: Path, verdicts_file: Path) -> None:
    rows = read_jsonl(responses_file)
    verdicts = {v["i"]: v for v in read_jsonl(verdicts_file)}
    missing = [r["i"] for r in rows if r["i"] not in verdicts]
    if missing:
        raise SystemExit(f"Faltam vereditos para os índices: {missing[:20]}{'…' if len(missing) > 20 else ''}")

    by_family = defaultdict(Counter)
    by_layer = defaultdict(Counter)
    overall = Counter()
    details = []
    for r in rows:
        v = verdicts[r["i"]]["verdict"]
        if v not in VERDICTS:
            raise SystemExit(f"Veredito desconhecido no item {r['i']}: {v!r}")
        overall[v] += 1
        by_family[r.get("family", "?")][v] += 1
        by_layer[str(r.get("layer", "?"))][v] += 1
        details.append({"i": r["i"], "family": r.get("family"), "layer": r.get("layer"),
                         "verdict": v, "reason": verdicts[r["i"]].get("reason")})

    n = len(rows)
    report = {
        "n": n,
        "overall": dict(overall),
        "accuracy_correct_only": round(overall["correct"] / n, 3),
        "accuracy_correct_or_partial": round((overall["correct"] + overall["partially_correct"]) / n, 3),
        "by_family": {k: dict(v) for k, v in sorted(by_family.items())},
        "by_layer": {k: dict(v) for k, v in sorted(by_layer.items())},
    }
    out = OUT_DIR / "math_rigor_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"report": report, "details": details}, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nDetalhes por item → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["prepare", "apply"])
    ap.add_argument("responses", type=Path)
    ap.add_argument("verdicts", type=Path, nargs="?")
    a = ap.parse_args()
    if a.mode == "prepare":
        prepare(a.responses)
    else:
        if not a.verdicts:
            raise SystemExit("apply exige o arquivo de vereditos")
        apply(a.responses, a.verdicts)
