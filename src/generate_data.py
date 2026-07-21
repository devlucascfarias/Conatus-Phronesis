"""Planejador de tasks de geração (Fases 1 e 2).

A geração dos exemplos NÃO usa API externa: quem escreve os exemplos é o Claude Code,
seguindo prompts/generator_system.md. Este script só monta o plano de tasks
(camada, propriedade, tópico, idioma, registro, flags) com as proporções do
gen_config.yaml, de forma determinística por --seed.

Uso:
    python src/generate_data.py --pilot                 # 20 tasks-piloto (Fase 1)
    python src/generate_data.py --n 500 --seed 43       # lote da Fase 2

Saída: data/raw/tasks_<nome>.jsonl — o Claude Code então escreve um exemplo por task
em data/raw/<nome>.jsonl, no formato {"layer", "lang", "messages": [...], "_task": {...}}.
"""
import argparse
import json
import random

from common import ROOT, load_yaml, read_jsonl

RAW_DIR = ROOT / "data" / "raw"


def build_tasks(cfg: dict, seeds: list[dict], n: int, rng: random.Random) -> list[dict]:
    layers = cfg["layers"]
    names = list(layers)
    weights = [layers[k]["share"] for k in names]
    lang_names = list(cfg["mix"]["lang"])
    lang_weights = [cfg["mix"]["lang"][k] for k in lang_names]
    tasks = []
    for i in range(n):
        layer = rng.choices(names, weights)[0]
        pool = [s for s in seeds if s["layer"] == layer]
        if not pool:
            raise SystemExit(f"Nenhum seed para a camada {layer} em data/seeds/seeds.jsonl")
        seed = rng.choice(pool)
        tasks.append({
            "task_id": i + 1,
            "layer": layer,
            "property": seed.get("property"),
            "topic": seed["topic"],
            "lang": rng.choices(lang_names, lang_weights)[0],
            "register": "informal" if rng.random() < cfg["mix"]["register_informal"] else "formal",
            "multi_turn": rng.random() < cfg["mix"]["multi_turn_share"],
            "imperfect_tool": layer in ("1", "2") and rng.random() < cfg["mix"]["imperfect_tool_responses"],
            "self_correction": layer == "2" and rng.random() < cfg["mix"]["layer2_selfcorrection"],
            "preamble_max_words": layers[layer]["preamble_max_words"],
        })
    return tasks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=None)
    ap.add_argument("--pilot", action="store_true", help="pilot_size tasks (Fase 1)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--name", type=str, default=None)
    args = ap.parse_args()

    cfg = load_yaml("configs/gen_config.yaml")
    seeds = read_jsonl(ROOT / "data" / "seeds" / "seeds.jsonl")
    n = cfg["dataset"]["pilot_size"] if args.pilot else (args.n or cfg["dataset"]["target_total"])
    tasks = build_tasks(cfg, seeds, n, random.Random(args.seed))

    name = args.name or ("pilot" if args.pilot else f"batch_{args.seed}_{n}")
    out = RAW_DIR / f"tasks_{name}.jsonl"
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    from collections import Counter
    print(f"{n} tasks → {out}")
    print("camadas:", dict(Counter(t["layer"] for t in tasks)))
    print("idiomas:", dict(Counter(t["lang"] for t in tasks)))
    print(f"Próximo passo: Claude Code escreve os exemplos em data/raw/{name}.jsonl "
          f"seguindo prompts/generator_system.md, e roda validate_data.py em seguida.")


if __name__ == "__main__":
    main()
