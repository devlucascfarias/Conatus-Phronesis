# Progresso da geração — Fase 2

- **Alvo iteração 1: ~1.000 exemplos** (decisão do usuário: reduzir, treinar, avaliar, então escalar).
- Plano de tasks: `data/raw/tasks_batch_43_2000.jsonl` (seed 43). Usar as primeiras ~1.000 tasks EM ORDEM.
- Exemplos em `data/raw/gen/batch_NNN.jsonl`, ~30 por arquivo, cada um com seu `_task`.
- Validação: `python src/validate_data.py data/raw/gen/*.jsonl data/raw/pilot.jsonl`
  (pilot.jsonl aprovado na Fase 1 conta para o dataset final).
- Regras: prompts/generator_system.md. Camada 0.5 = rationale em parágrafo separado (linha em branco)
  antes da resposta. Camada 2 = stdout do sandbox EXATO (validador executa o código de verdade).

## Estado

- Batches concluídos: **001**–**011** (300 base + 16 suplemento camada 3)
- Pilotos Fase 1: 20 exemplos aprovados (`data/raw/pilot.jsonl`)
- **Total aprovado: 336** (316 gerados + 20 pilotos), 336/336 na validação
- Próximo passo: treinar o 4B na Fase 3 e avaliar na Fase 4; análise de erro guia se vale escalar além de 300

### Lições recorrentes (evitar retrabalho)
- **Camada 0.5 SEMPRE com rationale em parágrafo próprio + linha em branco + resposta.** O validador
  mede o primeiro parágrafo do último turno; rationale colado à resposta estoura o limite de 25 palavras.
- **Camada 2: stdout do sandbox tem que bater com a execução real** (arredondamento de float inclusive —
  ex.: 249.90*0.85 imprime 212.41, não 212.42). Pré-calcular antes de escrever.

### Suplemento camada 3 (batch 011)
16 exemplos que combinam web_search de dado atual + raciocínio longo (3 encadeiam busca→sandbox→raciocínio: payback solar, quitar-vs-investir, índice preço-aluguel). Preenche o buraco identificado: nenhum dos 8 exemplos camada 3 originais combinava tool com raciocínio. Camada 3 subiu de 2.5%% para 7.1%% (acima do alvo de 5%%, intencional).
