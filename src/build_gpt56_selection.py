"""Monta a selecao do GPT-5.6 a incluir no proximo treino, protegendo a
proporcao ja calibrada por eval real de camadas 0/0.5/1/C (nao mexe nelas).

Decisao: manter TODO o pipeline original (479 itens) intocado. Da trilha
GPT-5.6 (466 itens), incluir:
  - calculo_rapido (50) e multiturno (16) inteiros — cobrem comportamento
    (autocorrecao, reacao a follow-up) que nao existe em nenhum outro lugar
    do dataset, entao diluir seria perder a licao.
  - uma amostra estratificada de 34 itens de camada 3 das 8 familias
    "dificeis" (~4-5 por familia) — da bastante peso ao reforco de rigor
    sem deixar camada 3 dominar o dataset combinado.
  - NADA das metades de camada 2 dessas 8 familias (ficam de fora deste
    treino, continuam salvas nos arquivos brutos pra uso futuro).

Resultado esperado: total combinado ~579, com camada 1 (web_search) em
~25% (vs 30% atual, redução real mas nao pela metade) e camada 2/3 em
~25%/~10% (reforco real sem estourar o dataset).
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
EXTRA_FAMILIES = {"data/raw/gpt56_algebra_linear.jsonl", "data/raw/gpt56_analise_complexa.jsonl"}


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
    n = 5 if fp in EXTRA_FAMILIES else 4
    picked = camada3[:n]
    print(fp, "-> selecionados", len(picked), "de", len(camada3), "camada 3")
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
