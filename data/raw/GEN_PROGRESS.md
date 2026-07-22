# Progresso da geração — Fase 2

- **Alvo iteração 1: ~1.000 exemplos** (decisão do usuário: reduzir, treinar, avaliar, então escalar).
- Plano de tasks: `data/raw/tasks_batch_43_2000.jsonl` (seed 43). Usar as primeiras ~1.000 tasks EM ORDEM.
- Exemplos em `data/raw/gen/batch_NNN.jsonl`, ~30 por arquivo, cada um com seu `_task`.
- Validação: `python src/validate_data.py data/raw/gen/*.jsonl data/raw/pilot.jsonl`
  (pilot.jsonl aprovado na Fase 1 conta para o dataset final).
- Regras: prompts/generator_system.md. Camada 0.5 = rationale em parágrafo separado (linha em branco)
  antes da resposta. Camada 2 = stdout do sandbox EXATO (validador executa o código de verdade).

## Estado

- Batches concluídos: **001**–**012** (300 base + 16 camada 3 + 47 corretivo)
- Pilotos Fase 1: 20 exemplos aprovados (`data/raw/pilot.jsonl`)
- **Total aprovado: 383** (363 gerados + 20 pilotos), 383/383 na validação
- Próximo passo: treinar o 4B na Fase 3 e avaliar na Fase 4; análise de erro guia se vale escalar além de 300

### Lições recorrentes (evitar retrabalho)
- **Camada 0.5 SEMPRE com rationale em parágrafo próprio + linha em branco + resposta.** O validador
  mede o primeiro parágrafo do último turno; rationale colado à resposta estoura o limite de 25 palavras.
- **Camada 2: stdout do sandbox tem que bater com a execução real** (arredondamento de float inclusive —
  ex.: 249.90*0.85 imprime 212.41, não 212.42). Pré-calcular antes de escrever.

### Suplemento camada 3 (batch 011)
16 exemplos que combinam web_search de dado atual + raciocínio longo (3 encadeiam busca→sandbox→raciocínio: payback solar, quitar-vs-investir, índice preço-aluguel). Preenche o buraco identificado: nenhum dos 8 exemplos camada 3 originais combinava tool com raciocínio. Camada 3 subiu de 2.5%% para 7.1%% (acima do alvo de 5%%, intencional).

### Lote corretivo (batch 012) — pós-avaliação da iteração 1
A Fase 4 do 4B mostrou regressão no recall de web_search (0.75→0.35): o modelo aprendeu a NÃO
buscar (super-aplicou o padrão da 0.5, virou hedge sem buscar, às vezes alucinou). 47 exemplos
dirigidos: ~26 camada 1 'volátil→busca→resposta confiante' (sem hedge), 6 pares contrastivos
0.5-vs-1, 8 camada 2 'mostra conta compacta→CHAMA o sandbox', 4 'na dúvida, busca primeiro'.
Camada 1 subiu p/ 25.1% (no alvo). imperfect_tool_responses reduzido 0.10→0.06 no gen_config.
