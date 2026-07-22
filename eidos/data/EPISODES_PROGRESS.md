# Progresso do dataset Eidos — Fase 1/2

- **Meta (decisão do sócio, 2026-07-22): 50 exemplos POR CAMADA × 6 = 300 episódios**,
  com CoT técnico desenvolvido (substituiu o piloto de ~20 do plano original).
- Spec: `prompts/generator_eidos.md`. Builder: `build_episodes.py` (execução real,
  outputs autênticos, QA por `expect`).
- Fonte = `batch_eNNN.py` (código); dado = `episodes_eNNN.jsonl` (commitados juntos).
- Regra de ouro: NENHUM arquivo/bug/prompt do `eval_cases.jsonl` reusado (testset).

## Estado

| Camada | Meta | Feito | Batches |
|---|---|---|---|
| L1 ciclo completo | 50 | 4 | e001 |
| L2 entrega verificada | 50 | 3 | e001 |
| L3 investigação autônoma | 50 | 3 | e001 |
| L4 estilo completo | 50 | 3 | e001 |
| L5 recuperação de tool | 50 | 3 | e001 |
| LC conversa técnica | 50 | 4 | e001 |
| **Total** | **300** | **20** | |

## Batches

### e001 (20 ep) — o lote de ouro
Fixa o padrão de cada camada. L1: import quebrado em merge, TS2366 de retorno faltante,
JSX não fechado, typo de método (en). L2: OrderSummary, RatingStars (a11y de SVG),
QuantityPicker (client). L3: recusa colar código ("eu leio direto"), dependência fantasma,
recusa screenshot (en). L4: auditoria completa em edit único — PromoTile (7 pendências),
SubscribeBox (6, com a11y de label), StatChip (en). L5: chave errada file_path→path,
edit ambíguo (old aparece 2x), comando rm bloqueado→npm install. LC: Tailwind vs Modules,
Zustand vs Context, "use client em tudo" (pushback respeitoso), dark mode em tool interno (en).

## Lições de construção (evitar retrabalho)

- Todo bug plantado precisa de `expect` no primeiro tsc (QA: quebra como prometido).
- Camadas de código fecham com `verify_green()` — sem exceção.
- Arquivos plantados novos são typecheckados junto: só podem importar o que existe no template.
- `ls` NÃO funciona no builder local (Windows/cmd) — localizar arquivo pelo erro do tsc,
  que é o padrão que queremos ensinar de qualquer forma.
- Variar: código de erro TS, registro do usuário, nº de ações (2-6), ~15% en.
