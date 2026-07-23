"""Gera as respostas do modelo pro held-out de rigor matemático (Fase 4+).

data/eval/math_rigor_testset.jsonl tem 40 itens (camada 2/3, nunca usados em
treino) com resolução de referência completa, incluindo \\boxed{} quando o
problema pede um resultado fechado. eval_harness.py mede escolha de tool e
comprimento de preâmbulo — nunca mediu se o raciocínio em si está certo. Este
script só gera as respostas; a nota (src/score_math_rigor.py) é dada por
Claude Code lendo par a par, mesmo padrão de src/judge_data.py.

Uso (Colab, mesma GPU do treino):
    python src/run_math_rigor_eval.py --model Qwen/Qwen3-8B --adapter outputs/adapter_8b \
        --out outputs/math_rigor_responses.jsonl
"""
import argparse
import json
from pathlib import Path

from common import ROOT, load_tools, read_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--testset", type=Path, default=ROOT / "data" / "eval" / "math_rigor_testset.jsonl")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs" / "math_rigor_responses.jsonl")
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

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for i, case in enumerate(cases, 1):
            question = next(m["content"] for m in case["messages"] if m["role"] == "user")
            reference = next(m["content"] for m in case["messages"] if m["role"] == "assistant")

            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": question}], tools=tools, tokenize=False,
                add_generation_prompt=True, enable_thinking=True,
            )
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            with torch.no_grad():
                # Mesma seed determinística por caso do eval_harness.py — reprodutível
                # entre rodadas, mesmo com do_sample=True (evita o loop de repetição do
                # greedy, ver data/eval/thinking_8b_eval_notes.md).
                torch.manual_seed(2000 + i)
                out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=True,
                                     temperature=0.6, top_k=20, top_p=0.95,
                                     repetition_penalty=1.15, no_repeat_ngram_size=8,
                                     pad_token_id=tokenizer.eos_token_id)
            response = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

            f.write(json.dumps({
                "i": i,
                "family": case.get("_eval_source_family"),
                "layer": case.get("layer"),
                "question": question,
                "reference": reference,
                "response": response,
            }, ensure_ascii=False) + "\n")

            if i % 5 == 0 or i == len(cases):
                print(f"  {i}/{len(cases)}")

    print(f"\n{len(cases)} respostas → {args.out}")
    print("Próximo passo: python src/score_math_rigor.py prepare", args.out)


if __name__ == "__main__":
    main()
