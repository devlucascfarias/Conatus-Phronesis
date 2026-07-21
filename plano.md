# PLANO.md — SFT de Tool-Use Calibrado (Qwen3-4B-Instruct-2507)

> **Instruções para o Claude Code:** este arquivo é o plano mestre do projeto. Execute as fases em ordem. Cada fase tem critérios de aceite — não avance sem cumpri-los. O treino em si roda no Google Colab (L4); seu trabalho aqui no PC é construir todo o resto: scripts de geração de dados, curadoria, avaliação, o notebook de treino e o loop de inferência. Peça confirmação ao usuário antes de qualquer chamada de API paga.

---

## 1. Contexto e tese do projeto

Treinar via SFT (QLoRA) um modelo pequeno para **julgamento de uso de ferramentas**: decidir *quando* buscar na web, *quando* verificar cálculos num sandbox Python e *quando* simplesmente responder. O modelo base já sabe conversar e já conhece o formato de tool call — o SFT instala o **critério**, não o formato.

Comportamento-alvo: raciocínio visível, curto e proporcional à dificuldade (esforço calibrado), com rationale explícito do porquê usar ou não usar cada ferramenta.

**Restrições:** Google Colab Pro, ~50 créditos, GPU L4 (24GB) como padrão, A100 como reserva. Orçamento de API para dados sintéticos definido pelo usuário antes da Fase 2.

## 2. Decisões técnicas fechadas (não rediscutir)

| Item | Decisão |
|---|---|
| Modelo base | `Qwen/Qwen3-4B-Instruct-2507` (variante **não-thinking**; NÃO usar a Thinking-2507) |
| Modelo cobaia | `Qwen/Qwen3-1.7B` para validar pipeline barato antes do treino final |
| Método | QLoRA 4-bit via **Unsloth** |
| Template | ChatML nativo do Qwen3 com `<tool_call>` / `<tool_response>`. Nunca inventar tags próprias. Sempre renderizar via `tokenizer.apply_chat_template` — nunca concatenar strings na mão |
| Raciocínio | Preâmbulo visível em texto comum antes da tool call (sem blocos `<think>`) |
| Tools (v1) | `web_search(query: str)` e `python_sandbox(code: str)`. Outras tools ficam para v2 |
| Idiomas | PT-BR dominante (~80%), EN minoritário (~20%) para reter capacidade bilíngue |
| Tamanho do dataset | Iteração 1: ~2.000 exemplos. Final: 3.000–8.000 conforme resultados |

## 3. Estrutura do repositório

```
sft-tool-judgment/
├── PLANO.md                     # este arquivo
├── configs/
│   ├── tools.json               # schemas das 2 tools (JSON Schema)
│   ├── gen_config.yaml          # proporções das camadas, limites de comprimento, temperatura
│   └── train_config.yaml        # hiperparâmetros de treino
├── prompts/
│   ├── generator_system.md      # prompt gerador de dados sintéticos
│   └── judge_system.md          # prompt do LLM-juiz para curadoria
├── src/
│   ├── generate_data.py         # geração sintética (chama API externa)
│   ├── validate_data.py         # filtros programáticos + dedup
│   ├── judge_data.py            # curadoria via LLM-juiz (opcional, se houver budget)
│   ├── build_dataset.py         # monta o JSONL final no chat template, com máscara de loss
│   ├── eval_harness.py          # avaliação: decisão de tool + comprimento de preâmbulo
│   └── inference_loop.py        # agente: gerar → detectar tool_call → executar → devolver
├── data/
│   ├── seeds/                   # tópicos-semente por camada (escritos à mão)
│   ├── raw/                     # saída bruta do gerador
│   ├── clean/                   # pós-validação/curadoria
│   └── eval/testset.jsonl       # ~120 casos de teste, escritos à mão, NUNCA gerados pelo mesmo prompt do treino
├── notebooks/
│   └── train_colab.ipynb        # notebook de treino (Unsloth, QLoRA)
└── outputs/                     # adapters, métricas, relatórios
```

## 4. Especificação do dataset

### 4.1 Camadas de esforço calibrado

| Camada | Tipo de pergunta | Formato da resposta | Limite de preâmbulo | % alvo |
|---|---|---|---|---|
| 0 | Trivial (fato estável, definição, conversa factual simples) | Resposta direta, **zero** preâmbulo, sem tool | 0 palavras | 20% |
| 0.5 | Fronteiriça (parece exigir busca, mas não exige) | Rationale breve de *não usar* + resposta | ≤ 25 palavras | 12% |
| 1 | Volátil / pós-cutoff / local / incerteza própria | Rationale (o que o usuário quer + propriedade + tool) + `<tool_call>` + turno com `<tool_response>` + resposta final citando o resultado | ≤ 40 palavras | 25% |
| 2 | Cálculo/física verificável | Resolução compacta (3–6 linhas) + `python_sandbox` + confirmação **ou autocorreção** | — | 18% |
| 3 | Genuinamente difícil | Raciocínio longo justificado (15–30 linhas), com ou sem tool | — | 5% |
| C | Conversa natural (papo, opinião, criatividade curta) | Resposta conversacional normal, sem tool | — | 20% |

**Regras transversais:**

- **Rationale com esqueleto fixo, redação variada.** Todo rationale das camadas 0.5 e 1 contém três elementos — (a) o que o usuário quer, (b) qual *propriedade* justifica a decisão, (c) qual tool resolve (ou por que nenhuma) — mas o fraseado deve variar entre exemplos. Proibir frase-fôrma repetida; o gerador deve produzir no mínimo 8 formulações distintas por propriedade.
- **Propriedades a cobrir na camada 1** (cada uma verbalizada nos rationales): volatilidade temporal (preços, cargos, placares, clima), eventos pós-cutoff (lançamentos, notícias), especificidade local (horários, endereços), falibilidade aritmética, incerteza própria sobre um dado.
- **Camada 2 obrigatoriamente inclui ~30% de casos de autocorreção**: o sandbox contradiz a resposta inicial e o modelo se corrige explicitamente e sem drama. Este é o exemplo mais valioso do dataset.
- **Multi-turno:** ~25% dos exemplos com 2–4 turnos de usuário, misturando camadas na mesma conversa (ex.: papo → pergunta volátil → follow-up trivial).
- **Tool responses realistas:** incluir resultados imperfeitos (busca que retorna pouco, resultado ambíguo, sandbox com erro de sintaxe que o modelo corrige e re-executa). ~10% da camada 1 e 2.

### 4.2 Tom de voz — brasileiro descontraído, sem exagero

O modelo deve soar como um brasileiro articulado conversando, não como tradução de manual nem como caricatura de "mano do grau". Diretrizes para o gerador (colocar verbatim no `generator_system.md`):

**Pode e deve (dosado):**
- Contrações naturais: "tá", "pra", "né" ocasional, "a gente" em vez de "nós"
- Aberturas leves quando cabem: "Boa pergunta", "Olha", "Então", "Beleza"
- Interjeições moderadas: "Opa", "Ah, isso muda rápido", "Hmm, deixa eu conferir"
- Vocabulário cotidiano: "conferir" > "verificar", "descolar" nunca, "checar" ok

**Proibido:**
- Gírias datadas ou forçadas: "mano", "véi", "top demais", "brabo", "cringe"
- Emoji (salvo se o usuário usar primeiro no exemplo)
- Diminutivos em cascata ("rapidinho", "certinho" — no máximo 1 a cada ~10 exemplos)
- Informalidade em conteúdo técnico denso: na camada 2 e 3, o raciocínio matemático é limpo e preciso; o tom descontraído aparece só na moldura ("Fechou, a conta bate:")

**Calibração:** ~60% dos exemplos com tom neutro-cordial, ~40% com traços descontraídos visíveis. O descontraído acompanha o registro do usuário: se o usuário escreve formal, a resposta volta ao neutro. Incluir pares demonstrando essa acomodação de registro.

### 4.3 Máscara de loss

No `build_dataset.py`, treinar loss **apenas nos tokens do assistant** (incluindo preâmbulos e tool calls). Mascarar: system, user e `<tool_response>` (o conteúdo da tool é input, não comportamento a imitar). Verificar com um teste unitário que imprime os spans mascarados de 3 exemplos.

## 5. Fases de execução

### Fase 0 — Setup e baseline (PC + 1 sessão curta de Colab)
1. Criar estrutura do repo, `tools.json`, configs.
2. Escrever à mão `data/eval/testset.jsonl`: ~120 casos rotulados — 40 que exigem `web_search`, 20 que exigem `python_sandbox`, 40 que NÃO exigem tool nenhuma (incluindo 15 fronteiriços "pegadinha"), 20 de conversa. Campos: `messages`, `expected_tool` (`web_search` | `python_sandbox` | `none`), `layer`, `lang`.
3. Rodar o modelo base cru no testset (Colab, L4, sem treino) via `eval_harness.py`. Salvar em `outputs/baseline_metrics.json`.
   - **Aceite:** métricas de baseline registradas: precisão/recall da decisão por tool, taxa de tool call com JSON válido, mediana de tokens de preâmbulo por camada.

### Fase 1 — Prompt gerador
1. Escrever `prompts/generator_system.md` incorporando TODA a seção 4 (camadas, propriedades, limites, tom, variação de fraseado). O gerador recebe: camada-alvo, propriedade-alvo, tópico-semente, idioma, registro do usuário (formal/informal) e devolve o exemplo completo em JSON estruturado (lista de messages).
2. Escrever ~150 tópicos-semente à mão em `data/seeds/` distribuídos por camada, com diversidade de domínio (economia, esporte, tech, cotidiano, ciência, cultura BR).
3. Gerar **20 exemplos-piloto** e parar. Apresentar ao usuário para revisão manual do tom e da qualidade dos rationales.
   - **Aceite:** usuário aprova os 20 pilotos (ou o prompt é iterado até aprovar).

### Fase 2 — Geração e curadoria (~2.000 exemplos)
1. `generate_data.py`: geração em lotes, com temperatura ~0.9 para diversidade, respeitando proporções do `gen_config.yaml`. Confirmar custo estimado da API com o usuário antes de rodar.
2. `validate_data.py`, filtros programáticos (rejeitar e logar motivo):
   - JSON de tool call inválido contra o schema de `tools.json`
   - Preâmbulo acima do limite de palavras da camada
   - Camada 0 com preâmbulo > 0
   - Frase-fôrma repetida: n-gramas (n=6) de rationale com frequência > 3 no corpus
   - Dedup por similaridade (embeddings ou MinHash, threshold agressivo)
   - Vazamento de gírias proibidas (lista da seção 4.2)
   - Camada 2: executar de verdade o código do `python_sandbox` dos exemplos e conferir que o resultado bate com o que o exemplo afirma
3. (Se houver budget) `judge_data.py`: LLM-juiz dá nota 1–5 para correção do rationale e naturalidade do tom; descartar < 4.
   - **Aceite:** ≥ 1.800 exemplos limpos em `data/clean/`, relatório de rejeição por motivo, distribuição final por camada dentro de ±3pp do alvo.

### Fase 3 — Treino (Colab)
1. `train_colab.ipynb` com Unsloth: carregar 4-bit, LoRA r=16, alpha=32, dropout=0.05, targets nos módulos de atenção+MLP; lr 2e-4 com cosine, warmup 3%, 1 época, batch efetivo ~16 (grad accum), max_seq_len 4096, `train_on_responses_only` do Unsloth alinhado à máscara da seção 4.3. Salvar adapter + versão merged em 16-bit para avaliação.
2. **Rodar primeiro no Qwen3-1.7B** (cobaia): valida que o pipeline treina, salva, carrega e que a loss desce. Custo baixo.
3. Treinar o 4B. Estimar créditos antes e reportar ao usuário; se a estimativa passar de 15 créditos, parar e discutir.
   - **Aceite:** adapter do 4B salvo, curva de loss sem anomalias, checkpoint carrega e gera no template correto.

### Fase 4 — Avaliação
1. Rodar `eval_harness.py` no modelo treinado, mesmo testset da Fase 0. O harness deve:
   - Parsear a decisão do modelo (tool chamada vs `expected_tool`) → precisão/recall/F1 por tool + matriz de confusão
   - Medir tokens de preâmbulo por camada → comparar com os alvos (camada 0 ≈ 0; camada 1 curto; camada 2 médio)
   - Validar JSON dos tool calls contra schema
   - Amostrar 20 respostas para revisão manual de tom pelo usuário
2. Gerar `outputs/report.md` comparando base vs treinado, com exemplos de erro categorizados (que critério o rationale aplicou errado?).
   - **Aceite:** relatório entregue. Meta indicativa da iteração 1: F1 da decisão ≥ baseline + 15pp e falso-positivo de busca em perguntas triviais < 10%. Se não bater, a análise de erros da Fase 4 alimenta ajuste de mistura e volta-se à Fase 2 (novo lote dirigido às classes de erro).

### Fase 5 — Loop de inferência (demo utilizável)
1. `inference_loop.py`: chat no terminal com o modelo treinado (via transformers ou llama.cpp/GGUF se o usuário quiser rodar local), com:
   - Executor de `web_search` (DuckDuckGo lib ou Tavily; chave em `.env`)
   - Executor de `python_sandbox`: subprocess com timeout de 5s, sem rede, whitelist de imports (math, numpy, sympy), capturando stdout/stderr
   - Loop: gerar → se `<tool_call>` presente, parsear, executar, injetar `<tool_response>`, gerar de novo (máx. 3 iterações de tool por turno)
   - **Aceite:** demo funcional nos 3 fluxos: busca, verificação com autocorreção, e conversa sem tool.

## 6. Orçamento de créditos (estimativa a validar na prática)

| Uso | Estimativa |
|---|---|
| Fase 0 (baseline, L4) | ~1–2 créditos |
| Fase 3 cobaia 1.7B (L4) | ~1–2 créditos |
| Fase 3 treino 4B, 1 época, ~2k exemplos (L4) | ~4–8 créditos |
| Fase 4 avaliação (L4) | ~1–2 créditos |
| Reserva para 2ª iteração + dataset maior | restante |

Regra: sempre reportar consumo real após cada sessão de Colab e atualizar esta tabela.

## 7. Fora de escopo da v1 (não fazer sem o usuário pedir)

- Outras tools além das duas definidas
- DPO/RL de qualquer tipo
- Treino full fine-tune
- Quantização final para deploy (GGUF) — só na Fase 5 se o usuário pedir
- Interface web

## 8. Riscos conhecidos e mitigação

- **Catastrophic forgetting da conversação** → camada C em 20% do dataset; conferir na Fase 4 com as 20 amostras manuais.
- **Modelo que busca tudo** → camadas 0 e 0.5 somam ~32%; falso-positivo é métrica de aceite.
- **Tom caricato** → filtro de gírias + revisão-piloto da Fase 1 + amostragem manual da Fase 4.
- **Estilo do gerador vazando (verbosidade)** → limites duros de palavras por camada, validados programaticamente.
- **Overfitting no testset** → testset escrito à mão, nunca tocado pelo gerador, nunca usado em treino.
