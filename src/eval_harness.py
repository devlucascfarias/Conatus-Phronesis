"""Avaliação: decisão de tool + comprimento de preâmbulo (Fases 0 e 4).

Roda no Colab (L4) ou em qualquer máquina com GPU:
    python src/eval_harness.py --model Qwen/Qwen3-8B --out outputs/baseline_metrics.json
    python src/eval_harness.py --model Qwen/Qwen3-8B --adapter outputs/adapter --out outputs/trained_metrics.json

Métricas: precisão/recall/F1 por tool, matriz de confusão, taxa de tool call com JSON
válido, mediana de palavras/tokens de preâmbulo por camada. Amostra 20 respostas para
revisão manual de tom em outputs/samples_for_review.md.
"""
import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from common import ROOT, extract_tool_calls, load_tools, preamble_text, read_jsonl, word_count

TOOLS = ("web_search", "python_sandbox", "none")


def predict_tool(text: str) -> tuple[str, bool]:
    """(tool prevista, json_valido). Sem tool call → ('none', True)."""
    calls = extract_tool_calls(text)
    if not calls:
        return "none", True
    first = calls[0]
    if "_invalid" in first:
        return "invalid", False
    name = first.get("name")
    args_ok = isinstance(first.get("arguments"), dict)
    return (name if name in TOOLS else "invalid"), args_ok


def prf(labels, preds, tool):
    tp = sum(1 for l, p in zip(labels, preds) if l == tool and p == tool)
    fp = sum(1 for l, p in zip(labels, preds) if l != tool and p == tool)
    fn = sum(1 for l, p in zip(labels, preds) if l == tool and p != tool)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3), "support": tp + fn}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None, help="pasta do adapter LoRA (Fase 4)")
    ap.add_argument("--testset", type=Path, default=ROOT / "data" / "eval" / "testset.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs" / "metrics.json")
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    ap.add_argument("--limit", type=int, default=None, help="avaliar só os N primeiros (debug)")
    args = ap.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto", device_map="auto")
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()

    tools = load_tools()
    cases = read_jsonl(args.testset)
    if args.limit:
        cases = cases[: args.limit]

    labels, preds, json_ok_flags, rows = [], [], [], []
    preamble_words = defaultdict(list)
    preamble_tokens = defaultdict(list)

    for i, case in enumerate(cases, 1):
        # O branch Qwen3-8B treina reasoning real nos itens difíceis de camada 3.
        prompt = tokenizer.apply_chat_template(
            case["messages"], tools=tools, tokenize=False, add_generation_prompt=True, enable_thinking=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        pred, json_ok = predict_tool(text)
        labels.append(case["expected_tool"])
        preds.append(pred)
        if pred != "none":
            json_ok_flags.append(json_ok)
        pre = preamble_text(text)
        preamble_words[case["layer"]].append(word_count(pre))
        preamble_tokens[case["layer"]].append(len(tokenizer(pre)["input_ids"]))
        rows.append({"id": case.get("id", i), "layer": case["layer"], "lang": case["lang"],
                     "expected": case["expected_tool"], "predicted": pred, "response": text})
        if i % 10 == 0 or i == len(cases):
            print(f"  {i}/{len(cases)}")

    confusion = Counter((l, p) for l, p in zip(labels, preds))
    trivial_ids = {r["id"] for r in rows if r["layer"] in ("0", "0.5", "C")}
    fp_search_trivial = sum(1 for r in rows if r["id"] in trivial_ids and r["predicted"] == "web_search")

    metrics = {
        "model": args.model, "adapter": args.adapter, "n_cases": len(cases),
        "per_tool": {t: prf(labels, preds, t) for t in TOOLS},
        "accuracy": round(sum(l == p for l, p in zip(labels, preds)) / len(labels), 3),
        "confusion_matrix": {f"{l}->{p}": c for (l, p), c in sorted(confusion.items())},
        "tool_call_json_valid_rate": round(sum(json_ok_flags) / len(json_ok_flags), 3) if json_ok_flags else None,
        "false_positive_search_on_trivial_rate": round(fp_search_trivial / max(1, len(trivial_ids)), 3),
        "preamble_words_median_by_layer": {k: statistics.median(v) for k, v in sorted(preamble_words.items())},
        "preamble_tokens_median_by_layer": {k: statistics.median(v) for k, v in sorted(preamble_tokens.items())},
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    with open(args.out.with_suffix(".responses.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    sample = random.Random(7).sample(rows, min(20, len(rows)))
    review = args.out.parent / "samples_for_review.md"
    with open(review, "w", encoding="utf-8") as f:
        f.write("# Amostras para revisão manual de tom\n\n")
        for r in sample:
            f.write(f"## {r['id']} (camada {r['layer']}, esperado: {r['expected']}, previsto: {r['predicted']})\n\n"
                    f"```\n{r['response']}\n```\n\n")

    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"Métricas → {args.out} | amostras de tom → {review}")


if __name__ == "__main__":
    main()
