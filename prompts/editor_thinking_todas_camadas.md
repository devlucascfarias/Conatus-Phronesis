# Brief para o GPT-5.6 — retrofit de `<think>` curto nas camadas 0/0.5/1/2/C

Este arquivo complementa `prompts/editor_thinking_gpt56.md` (que já cobre a camada 3 —
raciocínio longo da trilha de matemática/física). Aqui o alvo é o **resto do dataset**:
`data/raw/pilot.jsonl` e `data/raw/gen/batch_0XX.jsonl` (identidade, tool-calling de busca,
cálculo de rotina, curiosidades) + camada 2 da trilha GPT-5.6 (`data/raw/gpt56_*.jsonl`).

## Por que isto existe

A decisão original deste branch era treinar `<think>` só na camada 3 e manter
`enable_thinking=False` fixo na geração pras demais — mas isso exigiria uma heurística de
roteamento (decidir ANTES de gerar se a pergunta "merece" thinking) que não existe hoje.
Decisão nova: `enable_thinking=True` fica ligado pra tudo, e em vez de rotear por fora, o
próprio dataset ensina a **dosar o tamanho do `<think>` pela dificuldade real** — curto nas
camadas triviais, livre só na camada 3. Isso é mais robusto que um roteador externo: o
modelo aprende o padrão "pensar pouco quando é pouco, pensar muito quando é muito" a partir
dos próprios exemplos, e não depende de uma classificação prévia da pergunta que pode
errar.

## Tetos por camada

Já estão configurados em `configs/gen_config.yaml` → `think_max_words` e reforçados por
`src/validate_data.py`, que rejeita item acima do teto.

| camada | teto de `<think>` | o que cabe ali |
|---|---|---|
| 0 | 15 palavras | confirmar que é pergunta direta/factual, sem necessidade de tool nem elaboração |
| 0.5 | 25 palavras | notar a propriedade que justifica um rationale leve, sem tool |
| 1 | 35 palavras | avaliar volatilidade/especificidade que decide buscar (ou não) |
| 2 | 40 palavras | notar se o cálculo é propenso a erro o bastante pra merecer sandbox |
| C | 20 palavras | escolher o ângulo/fato antes de contar, sem virar redação |
| 3 | sem teto | já coberto por `editor_thinking_gpt56.md` — não mexer aqui |

Importante: **o `<think>` não conta como preâmbulo visível.** `strip_think_blocks()` em
`src/common.py` já exclui o bloco antes de medir `preamble_words_median_by_layer` — ou
seja, mesmo a camada 0 (que exige **zero** palavras de preâmbulo visível) pode ter um
`<think>` de até 15 palavras sem violar essa regra. São métricas independentes.

## O que entra no `<think>` aqui — é deliberação mínima, não um resumo do óbvio

Diferente da camada 3 (onde o `<think>` reconstrói uma dificuldade matemática real), aqui o
`<think>` é o **julgamento rápido que já acontece implicitamente** antes da resposta —
só que agora escrito. Não é redundante com o texto visível porque o texto visível (quando
existe rationale, camadas 0.5/1) já é a JUSTIFICATIVA formal pro usuário; o `<think>` é o
passo ainda mais cru, de decisão, que vem antes dela.

Por camada:

- **Camada 0** (resposta seca, sem preâmbulo): o `<think>` confirma que não há tool nem
  elaboração necessária. Ex.: `"Pergunta factual direta, resposta já sabida — sem tool,
  sem rodeio."` Nunca repita a mesma frase-molde em todos os itens (ver seção de variação
  abaixo).
- **Camada 0.5** (rationale leve, sem tool): o `<think>` nota a propriedade central antes
  de escrever o rationale visível. Ex.: pergunta sobre definição atemporal → `"Conceito
  estável, não muda com o tempo — não é caso de busca."`
- **Camada 1** (decisão de `web_search`): o `<think>` é o julgamento de volatilidade/
  especificidade/incerteza que já existe em `layer1_properties` de
  `configs/gen_config.yaml` (`volatilidade_temporal`, `evento_pos_cutoff`,
  `especificidade_local`, `incerteza_propria`) — só que dito antes, mais cru, decidindo
  buscar ou não.
- **Camada 2** (cálculo/sandbox): o `<think>` avalia se a conta é propensa a erro o
  bastante pra merecer o `python_sandbox` (mesmo critério que já rege quando usar tool
  nesta camada) — não refaz a conta em si, só decide o caminho.
- **Camada C** (curiosidade/conversa): o `<think>` escolhe o ângulo ou o fato antes de
  escrever — evita que a resposta visível saia genérica.

**Regra dura, igual à da camada 3**: o conteúdo/decisão final não pode mudar. Isso é
retrofit de formato — mesma tool (ou ausência dela), mesmo resultado, mesmo tom. O
`<think>` só explicita um julgamento que já estava implícito.

## Variação obrigatória — MAIS crítica aqui do que na camada 3

Com teto de 15-40 palavras e centenas de itens, o risco de frase-fôrma é alto (é
exatamente o padrão que `validate_data.py` já pune nas camadas 0.5/1 pro rationale
visível — `ngram_max_freq: 3`, ver seção "passe 2" do script). Isso **não é verificado
automaticamente pro `<think>`** (o filtro de 6-gramas roda só em `preamble_text()`, e o
`<think>` fica fora da métrica de preâmbulo) — então a responsabilidade de variar cai
inteiramente na geração. Peça ao GPT-5.6 pelo menos 10-15 formulações distintas de
abertura por lote de 30-50 itens da mesma camada, evitando qualquer fórmula fixa tipo
"Isso é uma pergunta [tipo], então..." repetida com o assunto trocado.

## O que NÃO editar

- Camada 3 (já coberta por `editor_thinking_gpt56.md`).
- Qualquer item cujo `layer` no JSON não seja um dos cinco valores-alvo.
- Turnos `tool` — nunca ganham `<think>` (não são turnos `assistant`).
- Em item multi-turno (vários turnos `assistant`), cada turno `assistant` ganha seu
  próprio `<think>` independente, sempre respeitando o teto da camada do item.

## Formato de saída

Igual ao documento-irmão: objeto JSON completo por linha, schema idêntico ao original
(`layer`, `lang`, `messages`, `_task` preservados), só o(s) `content` de turno `assistant`
reescritos com o prefixo `<think>\n...\n</think>\n\n`. Sem markdown ao redor, sem
`<tool_call>` dentro do `<think>`, um item por linha.

## Checklist antes de aceitar

1. Decisão final (tool escolhida, ausência de tool, conteúdo da resposta) idêntica ao
   item original.
2. `<think>` dentro do teto de palavras da camada (ver tabela) — `validate_data.py`
   rejeita automaticamente quem estourar (`think_acima_de_N_palavras`), mas revisar antes
   de mandar pra validação evita ida e volta.
3. `<think>` é julgamento real, não paráfrase do texto visível que já vem depois.
4. Sem abertura repetida verbatim entre itens da mesma camada no lote.
5. JSON válido, uma linha, resto do schema intacto.

## Onde isso vira dataset de verdade

1. Você recebe o JSONL editado do GPT-5.6.
2. Eu confiro contra o checklist acima.
3. Os aprovados substituem a versão sem `<think>` no arquivo de origem (mesmo arquivo,
   mesmo `_task.task_id`/posição — é edição, não item novo).
4. Rodo `python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl
   data/raw/gpt56_combined_selection.jsonl` — agora com `think_max_words` reforçando o
   teto automaticamente por camada.
5. Atualizo `data/raw/GEN_PROGRESS.md` com a contagem final antes de considerar este
   branch pronto pra retreinar.
