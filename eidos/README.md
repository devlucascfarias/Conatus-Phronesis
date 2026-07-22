# Eidos — Fase 0: harness de avaliação

Estrutura:

```
eidos/
  template_app/       app Next 14 + Tailwind pinado (referência viva do guia de estilo)
  style_guide.md      o "elegante e moderno" objetivo — checklist que os checks derivam
  tools.json          read_file / write_file / edit_file / run_terminal
  gen_eval_cases.py   fonte da verdade dos 100 casos (gera eval_cases.jsonl)
  eval_cases.jsonl    100 casos: fix-build 30, fix-visual 20, create-component 30, terminal-ops 20
  verify_cases.py     QA: confere que cada bug plantado quebra como o caso promete
  run_eval.py         o harness: agente + executores reais + checks + métricas
```

## Rodar o baseline (Fase 0) no Colab/L4

```bash
git clone <repo> && cd <repo> && git checkout conatus-eidos
cd eidos/template_app && npm install --no-audit --no-fund && cd ../..
# opcional, mas recomendado uma vez por máquina:
python eidos/verify_cases.py --skip-build

pip install -q transformers accelerate bitsandbytes
python eidos/run_eval.py --model Qwen/Qwen2.5-Coder-7B-Instruct
```

Saídas em `eidos/results/`: `metrics.json` (agregado) e `transcripts/<id>.json`
(episódio completo de cada caso, pra análise de erro).

Filtros úteis durante o desenvolvimento:

```bash
python eidos/run_eval.py --model ... --family fix-build       # só uma família
python eidos/run_eval.py --model ... --only fb-001,cc-005     # casos específicos
```

## Métricas

- `success_rate` (total e por família) — todos os checks do caso passaram.
- `avg_iterations` — quantas chamadas de tool até terminar.
- `tool_json_valid_rate` — JSON dos tool calls parseia.
- `reacted_to_error_rate` vs `blind_repeat_rate` — depois de um resultado de erro,
  o agente mudou a ação ou repetiu a mesma chamada identicamente? (O coração do Eidos:
  ler o erro e reagir.)

## Custos e avisos

- O workdir (`eidos/.work`) instala `node_modules` UMA vez e é resetado por caso
  (arquivos re-copiados do template, extras removidos, `.next` limpo).
- Checks `tsc` custam ~5-10 s; checks `build` custam ~40-90 s (só 4 casos fix-build
  usam build, onde o tsc não pega o erro Next-specific).
- Casos `terminal-ops` fazem `npm install` REAL de pacotes (rede necessária). O reset
  entre casos não desinstala do node_modules (inofensivo: o package.json volta ao
  template, então o check de dep não vaza entre casos).
- Rodada completa de 100 casos: estimar 1,5–3 h na primeira vez (dominada pela geração
  do modelo + installs). Use `--family`/`--only` pra iterar barato.
