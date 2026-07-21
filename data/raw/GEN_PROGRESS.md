# Progresso da geração — Fase 2

- **Alvo iteração 1: ~1.000 exemplos** (decisão do usuário: reduzir, treinar, avaliar, então escalar).
- Plano de tasks: `data/raw/tasks_batch_43_2000.jsonl` (seed 43). Usar as primeiras ~1.000 tasks EM ORDEM.
- Exemplos em `data/raw/gen/batch_NNN.jsonl`, ~30 por arquivo, cada um com seu `_task`.
- Validação: `python src/validate_data.py data/raw/gen/*.jsonl data/raw/pilot.jsonl`
  (pilot.jsonl aprovado na Fase 1 conta para o dataset final).
- Regras: prompts/generator_system.md. Camada 0.5 = rationale em parágrafo separado (linha em branco)
  antes da resposta. Camada 2 = stdout do sandbox EXATO (validador executa o código de verdade).

## Estado

- Batches concluídos: **001** (1–30), **002** (31–60), **003** (61–90)
- Pilotos Fase 1: 20 exemplos aprovados (`data/raw/pilot.jsonl`)
- **Total aprovado até agora: 110** (meta ~1.000)
- Próxima task a escrever: **91**

### Lições recorrentes (evitar retrabalho)
- **Camada 0.5 SEMPRE com rationale em parágrafo próprio + linha em branco + resposta.** O validador
  mede o primeiro parágrafo do último turno; rationale colado à resposta estoura o limite de 25 palavras.
- **Camada 2: stdout do sandbox tem que bater com a execução real** (arredondamento de float inclusive —
  ex.: 249.90*0.85 imprime 212.41, não 212.42). Pré-calcular antes de escrever.
