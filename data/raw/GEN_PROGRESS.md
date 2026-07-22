# Progresso da geração — Fase 2

- **Alvo iteração 1: ~1.000 exemplos** (decisão do usuário: reduzir, treinar, avaliar, então escalar).
- Plano de tasks: `data/raw/tasks_batch_43_2000.jsonl` (seed 43). Usar as primeiras ~1.000 tasks EM ORDEM.
- Exemplos em `data/raw/gen/batch_NNN.jsonl`, ~30 por arquivo, cada um com seu `_task`.
- Validação: `python src/validate_data.py data/raw/gen/*.jsonl data/raw/pilot.jsonl`
  (pilot.jsonl aprovado na Fase 1 conta para o dataset final).
- Regras: prompts/generator_system.md. Camada 0.5 = rationale em parágrafo separado (linha em branco)
  antes da resposta. Camada 2 = stdout do sandbox EXATO (validador executa o código de verdade).

## Estado

- Batches concluídos: **001**–**014** (300 base + 16 cam3 + 47 corretivo + 24 corretivo2 + 26 rebalanceamento)
- Pilotos Fase 1: 20 exemplos aprovados (`data/raw/pilot.jsonl`)
- **Total aprovado: 433** (413 gerados + 20 pilotos), 433/433 na validação
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

### Lote corretivo 2 (batch 013) — pós-avaliação da iteração 2
Iter-2 recuperou recall de web_search (0.35->0.525) e resolveu python_sandbox (0.65->0.95),
mas restaram 2 padrões de falha de busca: (1) 'é fixo, não preciso buscar' em horário/taxa
(museu, Selic) -> alucina; (2) 'não tenho acesso, consulte o site oficial' -> manda o usuário
buscar. 24 exemplos dirigidos: rationales que REJEITAM explicitamente 'é fixo' (horários de
museu/parque/biblioteca, taxas), e que REJEITAM o punt ('eu busco, não te mando procurar':
preços, shows, resultados), + 4 contrastivos estáveis (fundação vs horário). 
ATENÇÃO: camada 1 subiu p/ 30.7%% (alvo 25%%) e C caiu p/ 14.3%% (alvo 20%%) — desequilíbrio
deliberado pra fechar recall; vigiar na Fase 4 se surge over-search ou perda de conversa.

### Lote de rebalanceamento (batch 014) — pós-avaliação da iteração 3
Iter-3 fechou o problema de busca (accuracy 0.90, web_search F1 0.857, FP-trivial 0%), mas a
demo Fase 5 mostrou regressão de coerência conversacional (camada C em 14.3%% vs alvo 20%%).
Decisão (B) do STATUS_ITER3: 26 exemplos — 21 camada C (desabafo, comemoração, nostalgia,
opinião, criatividade curta, papo, perguntas pessoais à IA; 17 pt-BR + 4 en) + 5 camada 0,
SEM camada 1. Foco em coerência e tom natural, perguntas frescas fora do testset.
Pós-batch: C 18.2%%, camada 1 diluída p/ 28.9%%, camada 0 17.1%%. Total 433, 433/433 na validação.
Esperado na próxima eval: web_search/sandbox mantêm, camada C melhora (amostras + preâmbulo),
FP-trivial segue 0; vigiar na demo Fase 5 se a resposta de conversa volta a ficar coerente.
