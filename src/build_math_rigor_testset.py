"""Monta data/eval/math_rigor_testset.jsonl: eval held-out de rigor matematico.

O eval_harness.py so mede escolha de tool (web_search/sandbox/nenhuma) e
comprimento de preambulo — nunca checou se o RACIOCINIO em si e correto ou
rigoroso. Isso deixava sem forma sistematica de medir se o treino corrigiu
os bugs documentados em prompts/generator_math_gpt56.md (indeterminacao
falsa, pular resolucao, autocontradicao, frase-forma).

Este script pega, de cada uma das 8 familias "dificeis" da trilha GPT-5.6,
itens que NAO entraram no treino (ver src/build_gpt56_selection.py: so os
4-5 primeiros de camada 3 por familia foram usados) e monta um eval
held-out: 3 de camada 2 (nenhum usado no treino) + 2 de camada 3 além dos
ja usados, por familia = 40 no total.

Uso: python src/build_math_rigor_testset.py
"""
import json

HARD_FAMILIES = [
    "data/raw/gpt56_limites.jsonl",
    "data/raw/gpt56_algebra_linear.jsonl",
    "data/raw/gpt56_matematica_fisica.jsonl",
    "data/raw/gpt56_fisica1.jsonl",
    "data/raw/gpt56_fisica2.jsonl",
    "data/raw/gpt56_fisica_computacional.jsonl",
    "data/raw/gpt56_analise_complexa.jsonl",
    "data/raw/gpt56_equacoes_diferenciais.jsonl",
]
# mesma regra de build_gpt56_selection.py: essas 2 familias tiveram 5 selecionadas p/ treino, o resto 4
EXTRA_FAMILIES = {"data/raw/gpt56_algebra_linear.jsonl", "data/raw/gpt56_analise_complexa.jsonl"}


def load(fp):
    with open(fp, encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def save(fp, rows):
    with open(fp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


testset = []

for fp in HARD_FAMILIES:
    rows = load(fp)
    camada2 = [r for r in rows if str(r["layer"]) == "2"]
    camada3 = [r for r in rows if str(r["layer"]) == "3"]
    n_used_c3 = 5 if fp in EXTRA_FAMILIES else 4

    picked_c2 = camada2[:3]
    picked_c3 = camada3[n_used_c3 : n_used_c3 + 2]

    family = fp.split("gpt56_")[1].replace(".jsonl", "")
    for r in picked_c2 + picked_c3:
        r["_eval_source_family"] = family
    testset.extend(picked_c2 + picked_c3)
    print(fp, "-> eval:", len(picked_c2), "camada2 +", len(picked_c3), "camada3")

save("data/eval/math_rigor_testset.jsonl", testset)
print("\ntotal no eval de rigor matematico:", len(testset))
