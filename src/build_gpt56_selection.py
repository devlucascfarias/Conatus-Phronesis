"""Monta a selecao do GPT-5.6 a incluir no proximo treino, protegendo a
proporcao ja calibrada por eval real de camadas 0/0.5/1/C (nao mexe nelas).

REVISAO pos-treino da v1 (34 itens de camada 3, ~10% do combinado): o eval real
mostrou regressao (accuracy 0.850->0.808, web_search recall 0.75->0.625,
web_search F1 0.833->0.758) e as amostras de revisao manual confirmaram queda
de disciplina de tool-calling generalizada — nao so em camada 1, tambem em
camada 2 (contas feitas so em prosa, sem chamar o sandbox). Suspeito principal:
o volume de prosa longa da camada 3 (~250 palavras medias) deslocou o registro
aprendido de "aciona a tool" pra "explica em texto".

Decisao revisada: reduzir a amostra de camada 3 de 34 para 2 por familia (16
no total) — mantem uma amostra pequena do reforco de rigor sem dominar o
dataset. calculo_rapido (50) e multiturno (16) continuam inteiros: sao camada
2 compacta e reforcam (nao competem com) a disciplina de tool-calling que
caiu. Das 8 familias "dificeis", entram tambem os 22 itens de camada 2 por
familia que nao pertencem ao held-out eval: os 3 primeiros ficam reservados
para avaliacao e camada2[3:] fornece 176 itens adicionais de treino.

Resultado esperado da trilha GPT-5.6: 258 itens, preservando a amostra reduzida
de camada 3 e incorporando integralmente a porcao treinavel de camada 2.
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
CAMADA3_POR_FAMILIA = 2  # v1 usava 4-5; reduzido apos regressao medida no eval


def load(fp):
    with open(fp, encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def save(fp, rows):
    with open(fp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


selection = []

for fp in HARD_FAMILIES:
    rows = load(fp)
    camada3 = [r for r in rows if str(r["layer"]) == "3"]
    picked = camada3[:CAMADA3_POR_FAMILIA]
    print(fp, "-> selecionados", len(picked), "de", len(camada3), "camada 3")
    selection.extend(picked)

for fp in HARD_FAMILIES:
    rows = load(fp)
    camada2 = [r for r in rows if str(r["layer"]) == "2"]
    picked = camada2[3:]
    print(
        fp,
        "-> selecionados",
        len(picked),
        "de",
        len(camada2),
        "camada 2 (3 reservados no held-out eval)",
    )
    selection.extend(picked)

for fp in ["data/raw/gpt56_calculo_rapido.jsonl", "data/raw/gpt56_multiturno.jsonl"]:
    rows = load(fp)
    print(fp, "-> incluido inteiro:", len(rows))
    selection.extend(rows)

# remove metadados de origem do gpt56 (_needs_execution ja nao deveria sobrar, mas por seguranca)
for r in selection:
    r.pop("_needs_execution", None)

save("data/raw/gpt56_combined_selection.jsonl", selection)
print("\ntotal selecionado da trilha GPT-5.6:", len(selection))
