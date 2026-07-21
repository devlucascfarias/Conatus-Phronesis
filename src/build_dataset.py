"""Monta o JSONL final no chat template do Qwen3, com máscara de loss (seção 4.3).

Loss APENAS nos tokens do assistant (preâmbulos e tool calls incluídos).
Mascarados: system, user e <tool_response> (conteúdo de tool é input, não comportamento).

Uso:
    python src/build_dataset.py data/clean/dataset.jsonl --out data/clean/train.jsonl
    python src/build_dataset.py data/clean/dataset.jsonl --show-masks   # teste: imprime spans de 3 exemplos

A renderização é SEMPRE via tokenizer.apply_chat_template — nunca concatenação manual.
A máscara é construída incrementalmente: renderiza messages[:i] e messages[:i+1] e marca
os tokens novos como treináveis somente se o turno i for do assistant.
"""
import argparse
import json
from pathlib import Path

from common import ROOT, load_tools, read_jsonl

IGNORE = -100


def render_ids(tokenizer, messages, tools):
    """Lista plana de ids. Em transformers >= 4.49-ish, tokenize=True devolve um BatchEncoding
    (dict-like), não uma lista de ints — extrai 'input_ids' explicitamente para não quebrar
    a decodificação/máscara com versões mistas do transformers."""
    out = tokenizer.apply_chat_template(messages, tools=tools, tokenize=True, add_generation_prompt=False)
    if hasattr(out, "keys") and "input_ids" in out:
        return list(out["input_ids"])
    return list(out)


def build_example(tokenizer, messages, tools):
    """Retorna (input_ids, labels). Turnos não-assistant (e o que o template injeta em volta) ficam IGNORE."""
    full_ids = render_ids(tokenizer, messages, tools)
    labels = [IGNORE] * len(full_ids)
    prev_len = 0
    for i in range(len(messages)):
        cur_ids = render_ids(tokenizer, messages[: i + 1], tools)
        if messages[i]["role"] == "assistant":
            for j in range(prev_len, min(len(cur_ids), len(full_ids))):
                labels[j] = full_ids[j]
        prev_len = len(cur_ids)
    return full_ids, labels


def show_masks(tokenizer, examples, tools, k=3):
    """Teste unitário visual: imprime os spans mascarados/treináveis de k exemplos."""
    for n, ex in enumerate(examples[:k], 1):
        ids, labels = build_example(tokenizer, ex["messages"], tools)
        print(f"\n===== EXEMPLO {n} (camada {ex.get('layer', ex.get('_task', {}).get('layer', '?'))}) =====")
        span_tokens, span_masked = [], labels[0] == IGNORE
        for tid, lab in zip(ids, labels):
            masked = lab == IGNORE
            if masked != span_masked:
                tag = "MASCARADO" if span_masked else "TREINÁVEL"
                print(f"[{tag}] {tokenizer.decode(span_tokens)!r}")
                span_tokens, span_masked = [], masked
            span_tokens.append(tid)
        tag = "MASCARADO" if span_masked else "TREINÁVEL"
        print(f"[{tag}] {tokenizer.decode(span_tokens)!r}")
        n_train = sum(1 for l in labels if l != IGNORE)
        print(f"--- {n_train}/{len(ids)} tokens treináveis ---")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "clean" / "train.jsonl")
    ap.add_argument("--model", default="Qwen/Qwen3-4B-Instruct-2507")
    ap.add_argument("--show-masks", action="store_true")
    ap.add_argument("--max-len", type=int, default=4096)
    args = ap.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    tools = load_tools()
    examples = read_jsonl(args.file)

    if args.show_masks:
        show_masks(tokenizer, examples, tools)
        return

    n_long = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for ex in examples:
            ids, labels = build_example(tokenizer, ex["messages"], tools)
            if len(ids) > args.max_len:
                n_long += 1
                continue
            text = tokenizer.apply_chat_template(ex["messages"], tools=tools, tokenize=False, add_generation_prompt=False)
            f.write(json.dumps({"text": text, "input_ids": ids, "labels": labels}, ensure_ascii=False) + "\n")
    print(f"{len(examples) - n_long} exemplos → {args.out} ({n_long} descartados por exceder {args.max_len} tokens)")
    print("No Colab, alinhe o train_on_responses_only do Unsloth com esta máscara "
          "(instruction_part='<|im_start|>user', response_part='<|im_start|>assistant').")


if __name__ == "__main__":
    main()
