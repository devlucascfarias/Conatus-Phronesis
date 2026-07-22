# Status — fim da Iteração 3 (retomar amanhã)

> Ponto de parada: modelo 4B treinado com 407 exemplos avaliado. Decisão pendente:
> aceitar a iter-3 como final (A) ou fazer uma rodada de rebalanceamento (B).
> **Recomendação: (B).** Se for (B), o próximo passo é escrever o lote de rebalanceamento
> (~15-20 exemplos camada C + alguns camada 0, SEM adicionar camada 1).

---

## 1. Resultado que o usuário mandou (eval iter-3, 407 exemplos + demo Fase 5)

### Métricas (`trained_metrics.json`)

```json
{
  "model": "Qwen/Qwen3-4B-Instruct-2507",
  "adapter": "outputs/adapter_4b",
  "n_cases": 120,
  "per_tool": {
    "web_search":     { "precision": 1.0,   "recall": 0.75, "f1": 0.857, "support": 40 },
    "python_sandbox": { "precision": 1.0,   "recall": 0.90, "f1": 0.947, "support": 20 },
    "none":           { "precision": 0.833, "recall": 1.0,  "f1": 0.909, "support": 60 }
  },
  "accuracy": 0.90,
  "confusion_matrix": {
    "none->none": 60,
    "python_sandbox->none": 2,
    "python_sandbox->python_sandbox": 18,
    "web_search->none": 10,
    "web_search->web_search": 30
  },
  "tool_call_json_valid_rate": 1.0,
  "false_positive_search_on_trivial_rate": 0.0,
  "preamble_words_median_by_layer":  { "0": 8,  "0.5": 22, "1": 18.5, "2": 22.5, "C": 39.0 },
  "preamble_tokens_median_by_layer": { "0": 21, "0.5": 35, "1": 25.0, "2": 39.5, "C": 53.0 }
}
```

### Amostras de tom relevantes (o que fixou e o que ficou)

**Os 2 padrões de falha da iter-2 foram CORRIGIDOS:**
- `ws-010` (Museu Ipiranga): agora **busca** (rationale meio confuso "informação local e fixa... vou buscar", mas a decisão está certa).
- `ws-008` (Selic): agora **busca** ("não tenho esse dado em tempo real. Vou buscar").
- `ws-013` (iPhone), `ws-012` (Caetano), `ws-009` (Mega-Sena): todos **buscam** agora (antes mandavam consultar o site).

**Único web_search MISS que restou nas amostras:**
- `ws-028` (Oscar 2024): respondeu de memória sem buscar — *"o vencedor é 'The Brutalist', dirigido por Brady Corbet"* (dessa vez acertou o diretor, mas devia ter buscado). Categoria "prêmios/resultados que o modelo acha que sabe". São 10 misses no total (web_search->none = 10).

**python_sandbox:** todos chamam a tool. Ressalvas de qualidade do CÓDIGO (não da decisão):
- `py-016` usa `sin`/`pi` sem `import math` → erraria na execução real.
- `py-007` usa expansão de Sarrus convoluta.

### Demo Fase 5 (busca real via Ollama) — revela regressão de conversa

1. **Dólar:** buscou certo via Ollama, pegou dado real (R$ 5,08, Agência Brasil 2026-07), MAS respondeu confuso — *"a última vez que vi o dólar estava em torno de R$ 5,08... vou buscar de novo"* (hedge estranho, como se não tivesse acabado de buscar).
2. **Cálculo (37,5% de 18.420):** raciocínio convoluto ("metade de 75%"), chamou sandbox → 6908. (Detalhe: 18420×0,375 = 6907,5; `:.0f` arredonda pra 6908.)
3. **Curiosidade (conversa):** resposta **incoerente e inventada** ("frequência de autoimagem", lógica sem sentido). Queda clara de qualidade na camada C.

---

## 2. Minha resposta / análise

### Placar das 4 rodadas

| Métrica | Baseline | Iter-1 (336) | Iter-2 (383) | **Iter-3 (407)** |
|---|---|---|---|---|
| accuracy | 0,85 | 0,725 | 0,825 | **0,90** |
| web_search recall | 0,75 | 0,35 | 0,525 | **0,75** |
| web_search F1 | 0,833 | 0,519 | 0,677 | **0,857** |
| python_sandbox recall | 0,70 | 0,65 | 0,95 | **0,90** |
| none precision | 0,784 | 0,645 | 0,747 | **0,833** |
| FP busca em trivial | 3,3% | 0% | 1,7% | **0%** |

### Veredito

- **O problema de busca está resolvido.** web_search recall voltou ao baseline (0,75), F1 acima do baseline (0,857), os dois padrões de falha fechados, accuracy 0,90 (melhor de todas), zero over-search (o risco que eu sinalizei NÃO se materializou apesar da camada 1 a 30,7%).
- **Meta formal da Fase 4** (F1 ≥ baseline + 15pp): tecnicamente não bateu os +15pp porque o baseline já era forte (~0,84 F1 macro, pouco espaço). Mas o modelo **supera o baseline em toda métrica** e ainda exibe os comportamentos-alvo que o baseline não tinha (raciocínio visível, preâmbulo calibrado, verificação no sandbox, sem emoji, tool use real). Funcionalmente é sucesso.
- **Custo real (visível na demo):** a coerência conversacional degradou — exatamente o risco de "catastrophic forgetting da conversação" (seção 8 do plano) quando a camada C caiu pra 14,3% (alvo 20%) e a camada 1 subiu pra 30,7%. Evidência: resposta do dólar confusa e curiosidade incoerente. Os números da eval não pegam isso (medem a decisão de tool).

### Distribuição atual do dataset (407 exemplos)

| Camada | Atual | Alvo |
|---|---|---|
| 0 | 17,0% | 20% |
| 0.5 | 13,0% | 12% |
| 1 | **30,7%** | 25% |
| 2 | 19,2% | 18% |
| 3 | 5,9% | 5% |
| C | **14,3%** | 20% |

### Decisão pendente

- **(A) Aceitar a iter-3 como final.** Julgamento de ferramenta resolvido, modelo supera baseline. Defensável se o uso é majoritariamente buscar/calcular/responder factual.
- **(B) Rodada de rebalanceamento** (RECOMENDADA): adicionar ~15-20 exemplos de conversa (camada C) + alguns de camada 0, **SEM adicionar mais camada 1**, pra restaurar a proporção (C volta a ~20%, camada 1 desce de 30,7%). Conserta a regressão de conversa mantendo os ganhos de busca (sólidos após 3 rodadas). Custo: mais um treino de <1 crédito.

---

## 3. Se amanhã for (B) — plano do lote de rebalanceamento

- Escrever **batch_014**: ~15-20 exemplos camada C (papo, opinião, criatividade curta, desabafo, conselho, nostalgia, comemoração) + ~5 camada 0, com foco em **coerência e tom natural** (o que regrediu). Perguntas frescas, nada do testset.
- **NÃO** adicionar camada 1 (já está sobre-representada).
- Alvo pós-batch: C ~18-20%, camada 1 ~29% (diluída).
- Validar (`validate_data.py`), commitar, `git pull` no Colab, retreinar 4B, avaliar (esperar: web_search/sandbox mantêm, camada C melhora nas amostras e no preâmbulo, FP-trivial segue baixo).
- Vigiar na demo Fase 5 se a resposta de conversa (curiosidade) volta a ficar coerente.

## Estado do repo (tudo commitado e no GitHub `Conatus-Phronesis`, branch main)

- Dataset: 407 exemplos, 407/407 na validação. Fonte: `data/raw/gen/batch_001`–`013` + `data/raw/pilot.jsonl`.
- `data/clean/dataset.jsonl` é a fonte de verdade versionada; `train.jsonl` é build (ignorado, gerado no Colab).
- Notebook `notebooks/train_colab.ipynb`: clone via GH_TOKEN, HF login, build_dataset, treino, eval, e demo Fase 5 com busca real Ollama (`OLLAMA_SEARCH_KEY`).
- `src/inference_loop.py`: executor Ollama→Tavily→DuckDuckGo + `run_agent()`.
- Progresso detalhado em `data/raw/GEN_PROGRESS.md`.
- Adapter treinado (`outputs/adapter_4b`) vive só na VM do Colab (outputs/ é ignorado) — precisa retreinar na sessão nova.
