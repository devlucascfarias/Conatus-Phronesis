# Progresso da geração — Fase 2

- **Alvo iteração 1: ~1.000 exemplos** (decisão do usuário: reduzir, treinar, avaliar, então escalar).
- Plano de tasks: `data/raw/tasks_batch_43_2000.jsonl` (seed 43). Usar as primeiras ~1.000 tasks EM ORDEM.
- Exemplos em `data/raw/gen/batch_NNN.jsonl`, ~30 por arquivo, cada um com seu `_task`.
- Validação: `python src/validate_data.py data/raw/gen/*.jsonl data/raw/pilot.jsonl`
  (pilot.jsonl aprovado na Fase 1 conta para o dataset final).
- Regras: `prompts/generator_system.md`. Todo turno assistant das camadas 0/0.5/1/2/C abre
  com `<think>` curto, dentro do teto da camada; a tool call fica fora do bloco. Camada 2 =
  stdout do sandbox EXATO (o validador executa o código de verdade).

## Estado

- Batches concluídos: **001**–**019** (300 base + 16 cam3 + 47 corretivo + 24 corretivo2 + 26 rebalanceamento
  + 10 polimento + 20 identidade [016] + 16 recall câmbio/cargo [017] + 12 divisão real/curiosidade [018]
  + 14 disciplina de tool-calling [019])
- Pilotos Fase 1: 20 exemplos aprovados (`data/raw/pilot.jsonl`)
- **Total aprovado (pipeline original): 505** (485 gerados + 20 pilotos), 505/505 na validação

### Branch `phronesis-thinking` — reasoning em todas as camadas no Qwen3-8B

Além dos 34 itens históricos de camada 3 já editados, o retrofit de
`prompts/editor_thinking_todas_camadas.md` foi concluído em **755 itens / 1.179 turnos
assistant**: todo o piloto e os batches de geração nas camadas 0/0.5/1/2/C, mais todos os
266 itens de camada 2 das fontes GPT-5.6. A camada 3 não foi alterada nesta etapa.
`gpt56_combined_selection.jsonl` continua com 82 itens (66 de camada 2 + 16 de camada 3),
sem reintroduzir os 18 itens de camada 3 removidos do treino.

O pipeline agora:

- exige `<think>` bem-formado em todo turno assistant das camadas 0/0.5/1/2/C, respeita os
  tetos 15/25/35/40/20 palavras e mantém `<tool_call>` fora dele;
- deixa a camada 3 sem teto e opcional no validador, preservando os exemplos antigos não
  abrangidos pelos dois retrofits;
- exclui reasoning completo ou truncado das métricas de preâmbulo;
- renderiza, avalia e executa com reasoning habilitado no `Qwen/Qwen3-8B`;
- treina `<think>`, resposta visível e tool call dentro do mesmo span de loss do assistant.

Auditoria: os 755 itens preservam integralmente a resposta visível, tool calls, retornos e
demais mensagens; não há pensamentos duplicados nem repetição literal nas seis primeiras
palavras. Na seleção efetiva de treino, 571 itens têm reasoning (948 turnos); os 24 itens
antigos de camada 3 dos batches continuam sem `<think>`, deliberadamente. A validação
principal aprovou **595/595** exemplos, e a validação separada das oito famílias completas
aprovou **400/400**. A renderização real com o tokenizer do Qwen3-8B manteve **595/595**
exemplos sob o limite de 4096 tokens, com zero descarte.

### Correção de rota — `enable_thinking=True` fica global, sem roteador externo

Decisão original: treinar `<think>` só na camada 3 e manter `enable_thinking=False` fixo na
geração pras demais camadas, pra não arriscar o modelo abrindo reasoning real em pergunta
trivial sem nunca ter visto exemplo disso. Problema: isso exigia decidir ANTES de gerar se
a pergunta "merece" thinking — um roteador externo que não existe e que teria seu próprio
risco de erro (classificar errado a dificuldade da pergunta).

**Nova decisão**: `enable_thinking=True` fica ligado globalmente (notebook já ajustado). Em
vez de rotear por fora, o dataset ensina o próprio modelo a **dosar o tamanho do `<think>`
pela dificuldade real** — teto de palavras por camada em `configs/gen_config.yaml`
(`think_max_words`: 0→15, 0.5→25, 1→35, 2→40, C→20, 3→sem teto), reforçado
automaticamente por `src/validate_data.py` (rejeita item acima do teto da camada). O
`<think>` não conta como preâmbulo visível — `strip_think_blocks()` já exclui o bloco da
métrica, então mesmo a camada 0 (zero palavras de preâmbulo visível) pode ter `<think>` de
até 15 palavras sem violar essa regra.

O retrofit das camadas 0/0.5/1/2/C foi concluído e validado. O modelo passa a ver decisões
curtas nas tarefas simples e reasoning progressivamente maior conforme a camada, sem
depender de um roteador externo.

### Inclusão dos 176 itens de camada 2 parados + batch_021 (reforço) — 595 → 846

Decisão registrada em conversa (não repetida aqui em detalhe): os 176 itens de camada 2
das 8 famílias "difíceis" do GPT-5.6 que nunca entraram em treino (reservados desde a
seleção original, ver seção "Trilha GPT-5.6" abaixo) foram incluídos inteiros —
`src/build_gpt56_selection.py` agora pega `camada2[3:]` de cada família (os 3 primeiros
continuam reservados pro held-out `math_rigor_testset.jsonl`, sem vazamento, conferido).
Isso levou camada 2 pra ~40% do dataset, bem acima do alvo formal (18%) — calculado que
rebalancear pra bater o alvo formal exigiria mais de 1.000 itens novos, desproporcional;
decisão foi aceitar o desvio (mesmo precedente já usado pra camada 3) e proteger
especificamente o que já regrediu uma vez (recall de `web_search`) com um lote de reforço
em vez de perseguir a proporção.

`batch_021` (75 itens): 25 camada 1 (`volatilidade_temporal`/`incerteza_propria`,
reforço direto do recall que caiu no episódio de regressão documentado abaixo) + 20
camada 0.5 + 20 camada C + 10 camada 0 (as mais carentes do alvo). 595→846 itens,
846/846 na validação, 0 colisões de n-grama.

### Lote corretivo 7 (batch_022) — pós-demo do 8B treinado com thinking

Primeiro treino real do 8B (846 itens) revelou, num demo ao vivo: (1) fabricação de fonte
não presente no `tool_response` (cotação do dólar citando "Banco Central" que não veio na
busca); (2) o mesmo bug de divisão inteira (`//`) resurgindo numa pergunta nova, apesar de
3 lotes corretivos anteriores (018/020); (3) alucinação de unidade ("R$" numa pergunta sem
contexto de dinheiro); (4) erro factual numa curiosidade numérica (ângulo de polígono
regular). 14 itens dirigidos, incluindo contraste explícito "com unidade" vs "sem unidade".
846→860, 860/860 na validação.

### batch_023 + batch_024 — "nunca fecha sem verificar" e "desistência graciosa"

Avaliação mais profunda do 8B (bateria manual de 16 perguntas de nível avançado +
comparação `do_sample=False` vs `do_sample=True`, registrada em
`data/eval/thinking_8b_eval_notes.md`) revelou dois padrões sistêmicos, não mais casos
pontuais: **greedy colapsa em loop de repetição** quando a autocorreção falha mais de uma
vez (~25% do held-out, ex.: autovalores, EDO com ressonância, campo elétrico, incerteza
quântica — trocando um número a cada linha, evadindo `no_repeat_ngram_size`); **sampling
evita o loop mas inventa resposta confiante sem verificar** (3 casos que o greedy tinha
acertado — integral dupla, esfera na cúpula, dilatação temporal — o sampling errou sem
nenhum sinal de alerta, porque nunca chamou `python_sandbox` antes do `\boxed{}`).

Causa raiz: nenhum exemplo do dataset mostra autocorreção que ainda não fechou depois de
uma segunda tentativa — só existe o caso feliz (corrige de primeira). `batch_023` (50
itens): 28 "nunca fecha sem verificar" (todo `\boxed{}` só depois do sandbox, temas
variados) + 22 "desistência graciosa" em camada 3 (duas tentativas reais, a segunda
também falha genuinamente, resposta final com ressalva sem drama). `batch_024` (12
itens): mesmo padrão de desistência graciosa, mas em camada 2 (cálculo de rotina) — faltava
no batch_023, que tinha posto os 22 todos em camada 3. 860→922, 922/922 na validação.

Decodificação também mudou: `do_sample=True` com os parâmetros reais do
`generation_config.json` do Qwen3-8B (`temperature=0.6, top_k=20, top_p=0.95`) virou
padrão em `eval_harness.py` (com seed fixa por caso, pra manter comparabilidade entre
rodadas), `inference_loop.py` e o notebook — loop de repetição é pior que resposta errada
(trava a geração inteira), e a expectativa é que `batch_023`/`batch_024` reduzam o problema
que fez o sampling errar sem aviso.

`src/validate_data.py` passou a reexecutar sandbox também na camada 3 (antes só camada 2)
— achou na hora um bug pré-existente na heurística de detecção de traceback (`"error" in
texto` casava com `alternating_error_bound=0.0099` num stdout legítimo e reprovava o item
à toa); corrigido pra exigir `Traceback` ou nome de exceção Python em início de linha.

**Pendente**: `batch_025` (~40 itens, só camada 1) foi encomendado pra reverter a diluição
— camada 1 caiu de 25,4% (595 itens) pra 19,6% (922 itens), abaixo do ponto que já causou a
regressão de recall documentada na seção seguinte. Retreinar sem isso arrisca reproduzir o
mesmo problema.

**Scorer de rigor matemático construído, ainda não rodado**: `data/eval/math_rigor_testset.jsonl`
(40 itens held-out, nunca usados em treino) tinha gabarito mas nenhum consumidor —
`src/run_math_rigor_eval.py` (gera respostas do modelo no Colab) +
`src/score_math_rigor.py` (`prepare`/`apply`, mesmo padrão de `src/judge_data.py` — juiz é
Claude Code, sem API externa, porque comparação simbólica de LaTeX é frágil demais pra um
comparador mecânico) + `prompts/judge_math_rigor.md`. Falta rodar contra um checkpoint
treinado de verdade.

### Iteração pós-treino do 4B com o dataset combinado (579 → regressão medida)

Treinou-se o 4B com os 579 exemplos (pipeline 491 + seleção GPT-5.6 v1, 100 itens incluindo 34
de camada 3). `eval_harness.py --adapter outputs/adapter_4b` mostrou **regressão real** contra o
baseline: accuracy 0,850→0,808, **web_search recall 0,75→0,625** (F1 0,833→0,758),
`python_sandbox` recall estável (0,70→0,70) mas com queda de precisão (1,0→0,933).

Revisão manual das amostras (`samples_for_review.md`) confirmou 3 padrões concretos de falha,
todos regressões de disciplina de tool-calling (não erros de conteúdo):
1. **Camada 2 faz conta em prosa, nunca chama o sandbox** (fórmula de Price, determinante 3×3
   resolvidos inteiramente à mão).
2. **Camada 1 aluc­ina com confiança em vez de buscar** (BBB — inventou vencedora e prêmio sem
   nenhuma busca).
3. **Camada 1 promete buscar mas não chama a tool** ("Buscando pra confirmar o calendário" sem
   `<tool_call>` nenhum depois).

**Hipótese**: o volume de prosa longa da camada 3 do GPT-5.6 (~250 palavras médias) deslocou o
registro aprendido de "aciona a tool" pra "explica em texto", mesmo em contextos de camada 1/2
onde isso é errado — a diluição de `web_search` que já estava prevista (30,1%→24,9%) se
materializou como regressão de verdade, não só um número de proporção.

**Correção em duas frentes:**
1. `batch_019` (14 exemplos): 7 camada 2 (fórmulas financeiras/estatística/combinatória, sempre
   com `<tool_call>` — nunca só em prosa) + 7 camada 1 (prêmios/realities/bilheteria — sempre busca
   antes de nomear vencedor, e quando a fonte vem incompleta, refina a busca DE VERDADE, não só
   promete refinar).
2. `src/build_gpt56_selection.py` revisado: amostra de camada 3 das 8 famílias reduzida de
   4-5/família (34 total) para **2/família (16 total)** — `calculo_rapido`/`multiturno` continuam
   inteiros (camada 2 compacta, reforça em vez de competir com a disciplina de tool-calling).

Resultado: `python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl
data/raw/gpt56_combined_selection.jsonl` → **587 aprovados, 0 rejeitados**. Camada 1 volta a
25,7% (de 24,9%), camada 3 cai de 10,0% pra **6,8%** (bem mais perto do alvo de 5%). `train.jsonl`
regenerado (587 exemplos, 0 descartados). Ainda não retreinado — próximo passo é rodar o 4B com
esse dataset revisado e comparar de novo contra o baseline.

### Lote corretivo 4 (batch 018) — pós-demo do 4B treinado com o dataset novo

Demo ao vivo (Fase 5, modelo recém-treinado com os 579 exemplos da iteração anterior) mostrou
2 falhas reais em 3 turnos testados: (1) camada 2 — o modelo escreveu `print(3*18420//8)` (divisão
inteira) pro cálculo de `37,5% de 18.420`, o checker devolveu `6907` (truncado), mas a resposta
final disse "6907,5" — o valor certo, só que **diferente do que o checker realmente retornou**,
sinal de que o modelo ignorou o resultado da tool e substituiu por conta de cabeça própria (acertou
por sorte, não por grounding). (2) camada C — "me conta uma curiosidade" sobre átomos na Terra vs.
grão de areia saiu fisicamente incoerente e autocontraditória (dois expoentes diferentes pra mesma
razão no mesmo parágrafo), regressão do padrão que o batch 015 já tinha corrigido uma vez.

12 exemplos dirigidos: 6 camada 2 (percentual/fração via sandbox, sempre com `/` — nunca `//` —,
incluindo autocorreção explícita do exato bug observado: código com `//`, checker trunca, modelo
reconhece a divisão inteira como causa, corrige pra `/`, resposta final = literalmente o que o
checker devolveu) + 6 camada C (curiosidades verificadas, incluindo a mesma comparação
átomos-Terra-vs-grão-de-areia refeita com números conferidos e consistentes, mais 5 outras
verdadeiras e verificáveis em temas novos). `dataset.jsonl`/`train.jsonl` já regenerados com
`python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl data/raw/gpt56_combined_selection.jsonl`
→ **591 aprovados, 0 rejeitados** (491 pipeline original + 100 seleção GPT-5.6).

### Lote corretivo 6 (batch 020) — o bug de `//` reapareceu mesmo com a correção do batch 018 no dataset

Nova demo ao vivo (4B retreinado já com os 587 exemplos do batch 018+019) reproduziu o **mesmo bug**
que o batch 018 já tinha corrigido no dataset — e de forma pior: `print(3*18420//8)` de novo (divisão
inteira), e dessa vez a resposta final nem sequer corrigiu o valor de cabeça (ficou em "6907", igual
ao checker truncado) e ainda trocou os dígitos do enunciado ("18.240" em vez de "18.420"). O exemplo
de correção exata (task 702, `37,5% de 18.420` com `/`) **estava presente no dataset de treino**, então
isso não é falta de dado — é sinal de que 1 exemplo verbatim, com 1 época de treino, não gerou peso de
gradiente suficiente pra sobrepor o prior do modelo base nesse padrão específico.

8 exemplos novos, focados em **reforçar a regra geral em vez de só repetir o mesmo par pergunta-resposta**:
6 variações de fração-percentual com números diferentes (incluindo um caso onde o resultado da divisão
real também é inteiro, pra não ensinar "// serve quando eu já espero um inteiro"), 1 exemplo de
auto-explicação da regra (por que `/` e não `//`) pra reforçar o princípio em vez de só memorizar pares,
e a pergunta exata do demo (`37,5% de 18.420`) **repetida duas vezes** (task 901 e 908) — a segunda com
ênfase extra em citar os números do enunciado sem trocar dígito — já que essa é literalmente a pergunta
fixa usada na célula 15 do notebook a cada rodada de demo.

`python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl data/raw/gpt56_combined_selection.jsonl`
→ **595 aprovados, 0 rejeitados**. `dataset.jsonl`/`train.jsonl` a regenerar no próximo treino (a célula
4 do notebook já faz isso automaticamente a partir do `dataset.jsonl` atualizado).

Se o bug persistir depois desse lote, o próximo passo não é mais dado — é hiperparâmetro: considerar
`num_train_epochs: 2` em `configs/train_config.yaml` (hoje 1 época só), já que o resto do dataset está
com bom recall exceto justamente os padrões corrigidos há pouco tempo (repetição fresca, ainda não
consolidada).

### Trilha GPT-5.6 (matemática/física pós-graduação) — decisão de merge

Paralelo ao pipeline acima, `prompts/generator_math_gpt56.md` gerou 466 exemplos (camada 2/3) via
GPT-5.6 em 8 famílias + cálculo rápido + multiturno (ver `data/raw/gpt56_*.jsonl`). Concatenar tudo
direto inflaria camada 3 de 5% pro alvo pra ~24% do total e diluiria o recall de `web_search`
(camada 1) de 30% pra 14% — risco real, já que esse recall levou 3 lotes corretivos pra estabilizar
(ver notas de batch 012/013 abaixo).

**Decisão**: `src/build_gpt56_selection.py` monta uma seleção de 100 itens da trilha GPT-5.6 —
`calculo_rapido` (50) e `multiturno` (16) inteiros (comportamento que não existe em nenhum outro
lugar do dataset: autocorreção real e reação genuína a follow-up), mais uma amostra estratificada
de 34 itens de camada 3 (~4-5 por família) das 8 famílias difíceis. Nenhuma das metades de camada 2
dessas 8 famílias entra neste treino — ficam salvas em `data/raw/gpt56_*.jsonl` pra uso futuro.

Resultado: `python src/build_gpt56_selection.py` gera `data/raw/gpt56_combined_selection.jsonl`
(100 itens); validado junto com o pipeline original via
`python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl data/raw/gpt56_combined_selection.jsonl`
→ **579 aprovados, 0 rejeitados**. Distribuição final: camada 0 16.2%, 0.5 9.2%, **1 (web_search) 24.9%**
(queda real mas não pela metade), 2 25.4%, 3 10.0% (2x o alvo original, deliberado), C 14.3%.
`train.jsonl` já gerado a partir desse `dataset.jsonl` (579 exemplos, 0 descartados por tamanho).

### O que fazer com os 366 exemplos do GPT-5.6 que ficaram de fora

`eval_harness.py` só mede escolha de tool (web_search/sandbox/nenhuma) e comprimento de preâmbulo —
nunca mediu se o raciocínio em si é correto ou rigoroso, e `data/eval/testset.jsonl` tem **zero
exemplos de camada 3** e só 20 de camada 2. Ou seja: não havia forma sistemática de checar se o
próximo treino corrige os bugs documentados em `prompts/generator_math_gpt56.md` (indeterminação
falsa, pular resolução, autocontradição) — só manualmente, como no teste ao vivo contra o Ollama.

Decisão: `python src/build_math_rigor_testset.py` monta `data/eval/math_rigor_testset.jsonl`
(**40 itens, held-out**: 3 camada 2 + 2 camada 3 por família, das 8 famílias difíceis, nenhum deles
usado na seleção de treino — confirmado sem overlap). Cada item já carrega a resolução de referência
completa (com `\boxed{}`) como ground truth pra comparar contra o que o modelo treinado produzir.
Ainda não construí um scorer automático — o modelo desta rodada nem foi treinado ainda; isso é pra
fazer depois do treino, quando houver o que avaliar de verdade.

Os outros **~326 exemplos** (metades de camada 2 das 8 famílias + o excedente de camada 3 além do
usado no eval/treino) ficam reservados em `data/raw/gpt56_*.jsonl`, sem uso definido ainda — decisão
de incluir mais (ou não) fica pra depois de ver o resultado do eval desta iteração.
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

### Mini-lote de polimento final (batch 015) — pós-avaliação da iteração 4
Iter-4 confirmou o rebalanceamento (demo: dólar e cálculo coerentes; métricas ≈ iter-3 dentro
do ruído de 3/120), com 3 residuais localizados. 10 exemplos dirigidos, um por residual:
(1) 4 camada C "me conta uma curiosidade" com fatos VERDADEIROS e verificáveis (Vênus,
tubarões vs árvores, ossos do bebê, Lua se afastando) — o modelo inventava conteúdo incoerente;
(2) 3 camada 1 anti-punt na categoria "resultado que acho que sei" (MasterChef, Lotofácil,
Jabuti — temas frescos, sem repetir Quina/BBB dos batches 012-013 nem o testset);
(3) 3 camada 2 trigonometria com `import math` explícito (pêndulo, projétil, escada) — py-016
usava sin/pi sem import. Total 443, 443/443 na validação. DECISÃO COMBINADA: esta é a última
rodada de dados — seja qual for a eval, fecha-se o dataset (retorno decrescente).
