"""Monta o JSONL final no chat template do Qwen3, com máscara de loss (seção 4.3).

Loss APENAS nos tokens do assistant (preâmbulos e tool calls incluídos).
Mascarados: system, user e <tool_response> (conteúdo de tool é input, não comportamento).

Uso:
    python src/build_dataset.py data/clean/dataset.jsonl --out data/clean/train.jsonl
    python src/build_dataset.py data/clean/dataset.jsonl --show-masks   # teste: imprime spans de 3 exemplos

A renderização é SEMPRE via tokenizer.apply_chat_template — nunca concatenação manual, e SEMPRE
de uma vez só (a conversa inteira). O Qwen3-8B extrai o reasoning de blocos <think> embutidos
em cada content de assistant. Renderizar prefixos messages[:i] incrementalmente faria cada
turno parecer "o último" na própria fatia e poderia desalinhá-lo. Por isso os spans do
assistant são localizados por offset de caractere numa única renderização completa — o mesmo
princípio do train_on_responses_only do Unsloth.
"""
import argparse
import json
from pathlib import Path

from common import ROOT, load_tools, read_jsonl

IGNORE = -100
ASSISTANT_MARKER = "<|im_start|>assistant\n"
TURN_MARKER = "<|im_start|>"


def assistant_spans(text: str) -> list[tuple[int, int]]:
    """Posições de caractere [início, fim) de cada turno do assistant no texto renderizado."""
    spans = []
    pos = 0
    while True:
        start = text.find(ASSISTANT_MARKER, pos)
        if start == -1:
            break
        content_start = start + len(ASSISTANT_MARKER)
        next_marker = text.find(TURN_MARKER, content_start)
        content_end = next_marker if next_marker != -1 else len(text)
        spans.append((content_start, content_end))
        pos = content_end
    return spans


def build_example(tokenizer, messages, tools):
    """Retorna (input_ids, labels, text). Turnos não-assistant (e o que o template injeta em volta) ficam IGNORE."""
    # Neste branch o alvo é o Qwen3-8B com reasoning habilitado. Em turnos já completos, o
    # template extrai <think> do content quando presente e deixa os demais turnos sem stub.
    text = tokenizer.apply_chat_template(
        messages, tools=tools, tokenize=False, add_generation_prompt=False, enable_thinking=True
    )
    enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = list(enc["input_ids"]), enc["offset_mapping"]
    spans = assistant_spans(text)
    labels = [IGNORE] * len(ids)
    for j, (tok_start, tok_end) in enumerate(offsets):
        if tok_start == tok_end:
            continue
        if any(s <= tok_start < e for s, e in spans):
            labels[j] = ids[j]
    return ids, labels, text


def show_masks(tokenizer, examples, tools, k=3):
    """Teste unitário visual: imprime os spans mascarados/treináveis de k exemplos."""
    for n, ex in enumerate(examples[:k], 1):
        ids, labels, _text = build_example(tokenizer, ex["messages"], tools)
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
    ap.add_argument("--model", default="Qwen/Qwen3-8B")
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
            ids, labels, text = build_example(tokenizer, ex["messages"], tools)
            if len(ids) > args.max_len:
                n_long += 1
                continue
            # `layer` viaja junto so pra permitir split de validacao estratificado no
            # notebook (camada 2 e ~40% do dataset; um split aleatorio nao representaria
            # as outras camadas). O treino em si remove tudo menos `text`.
            layer = str(ex.get("layer", ex.get("_task", {}).get("layer", "?")))
            f.write(json.dumps({"text": text, "layer": layer, "input_ids": ids, "labels": labels}, ensure_ascii=False) + "\n")
    print(f"{len(examples) - n_long} exemplos → {args.out} ({n_long} descartados por exceder {args.max_len} tokens)")
    print("No Colab, alinhe o train_on_responses_only do Unsloth com esta máscara "
          "(instruction_part='<|im_start|>user', response_part='<|im_start|>assistant').")


if __name__ == "__main__":
    main()
