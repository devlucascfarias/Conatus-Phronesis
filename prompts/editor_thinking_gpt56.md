# Brief para o GPT-5.6 (raciocínio xhigh) — retrofit de `<think>` nos itens de camada 3

Este arquivo é a instrução (system ou primeira mensagem) pra uma conversa com o GPT-5.6 cujo
objetivo NÃO é gerar problema novo — é **editar** itens já aprovados de
`data/raw/gpt56_*.jsonl` (a trilha de matemática/física do `prompts/generator_math_gpt56.md`)
pra adicionar um bloco `<think>` de deliberação real, mantendo a matemática e a resposta
final exatamente corretas como já estão.

Branch: `phronesis-thinking` (worktree separado de `new-model`, mesmo `.git`, histórico
independente a partir daqui). Esse experimento não mistura com o treino do 8B sem thinking
que está rodando em paralelo em `new-model` — é pra ser comparável depois, não substituir.

## Isto contradiz `generator_math_gpt56.md` de propósito

Aquele documento proíbe explicitamente bloco `<think>` (linha 22: "Proibido bloco
`<think>...</think>`"), porque o modelo-alvo até agora (`Qwen3-4B-Instruct-2507`) não tem
mecanismo de thinking — todo raciocínio precisa ser texto visível comum. **Aqui é o
oposto**: o alvo deste branch é `Qwen/Qwen3-8B`, um modelo híbrido que tem esse mecanismo
de verdade, e o objetivo do experimento é justamente testar se separar deliberação (oculta)
de resposta final (visível, mais enxuta) melhora rigor matemático sem inflar o preâmbulo
calibrado das outras camadas. Se você (Lucas) ou o GPT-5.6 confundir os dois documentos, o
resultado sai errado nos dois sentidos.

## Como o template do modelo-alvo trata `<think>` (verificado direto no chat_template real)

Inspecionei o `chat_template` do `Qwen/Qwen3-8B` via `AutoTokenizer.from_pretrained` antes
de escrever isto — não é suposição. O mecanismo, por turno `assistant`:

- O template procura uma chave separada `message.reasoning_content` primeiro; se não achar,
  faz *fallback* pra extrair de dentro do `content`: tudo entre `<think>` e `</think>` vira
  a "reasoning", e o resto do `content` (depois do `</think>`) vira a resposta visível.
- **Isso funciona por turno, não só no último da conversa** — testei e confirmei: se um
  `content` de um turno `assistant` no meio de uma conversa (ex.: antes de um `<tool_call>`)
  contém `<think>...</think>`, o template também extrai e renderiza esse bloco corretamente.
  Se um turno não tiver `<think>` no `content`, ele renderiza normal, sem nenhum stub vazio
  forçado. Ou seja: dá pra decidir, item por item e turno por turno, quais ganham thinking.
- **Nosso schema não precisa de campo novo.** Não usamos a chave `reasoning_content`
  separada — o jeito mais simples e compatível com o JSONL atual é escrever o `<think>` como
  parte literal da string de `content`, no início do turno `assistant`:
  `"<think>\n...deliberação...\n</think>\n\nresposta visível aqui"`.
- **O `<tool_call>` nunca fica dentro do `<think>`.** Ação estrutural (chamar a tool) é
  depois do `</think>`, igual ao resto do projeto — o `<think>` é só o raciocínio que
  precede a decisão de agir, não a ação em si.
- **Loss ainda é calculada em cima do `<think>`.** O `build_dataset.py` mascara por span de
  turno `assistant` inteiro (entre os marcadores do template) — o bloco `<think>` está
  dentro desse span, então ele entra no treino igual ao resto. Não é um canal "grátis" nem
  escondido do gradiente; se o conteúdo for fraco ou repetitivo, o modelo aprende o padrão
  fraco/repetitivo do mesmo jeito que aprenderia num texto visível ruim.

## Ajuste aplicado no pipeline

`src/common.py::preamble_text()` originalmente pegava tudo antes do primeiro `<tool_call>`
como "preâmbulo" e contava também o texto de `<think>`. Neste branch, `strip_think_blocks()`
remove blocos completos — e reasoning truncado sem `</think>` — antes das métricas.
`validate_data.py` também foi ajustado para exigir o formato no início do turno, aplicar
os tetos curtos das demais camadas e rejeitar qualquer `<tool_call>` colocado dentro do bloco.
Assim, `preamble_words_median_by_layer` continua comparável com o branch sem thinking.

## O que exatamente editar

Escopo: **camada 3** dos arquivos `data/raw/gpt56_*.jsonl` (os itens genuinamente difíceis —
prova de reordenação, EDPs, análise complexa etc., ver famílias em
`generator_math_gpt56.md`). Comece pelos 34 itens de camada 3 usados na seleção v1: os
primeiros quatro de cada família difícil, mais um quinto de álgebra linear e de análise
complexa. A seleção atual foi reduzida depois para 16 itens (os dois primeiros de cada
família) por `src/build_gpt56_selection.py`; portanto, edite os 34 nos arquivos de família
e regenere `data/raw/gpt56_combined_selection.jsonl`, que continuará contendo apenas o
subconjunto atual de 16. Os outros itens de camada 3 dentro dos arquivos completos são a
segunda leva, se o experimento for promissor.

Este documento continua sem editar camada 2 ou o pipeline original porque seu foco é a
deliberação longa da camada 3. Esses itens agora recebem `<think>` curto pelo documento
complementar `prompts/editor_thinking_todas_camadas.md`; portanto, não estão mais excluídos
do experimento como um todo.

## O que entra no `<think>` vs. o que fica visível

Cole o item já aprovado (JSON completo, `messages` incluído) e peça pro GPT-5.6 dividir o
`content` do turno `assistant` em duas partes:

1. **`<think>`: a deliberação real, não uma cópia do que já está escrito.** O texto atual
   de camada 3 já é a demonstração polida (é literalmente o "quinto bug real" que
   `generator_math_gpt56.md` documenta — texto de livro-texto, sem mostrar por que outras
   abordagens falhariam). O `<think>` é o lugar certo pra esse rastro que faltava: por que a
   abordagem óbvia não se aplica, qual é a dificuldade real antes de resolver, hesitação
   genuína entre duas técnicas plausíveis, um caminho tentado e abandonado quando fizer
   sentido pro problema. Estilo mais cru, "pensando alto" — frases mais curtas e diretas que
   a prosa técnica final, pode ter reconsiderações explícitas ("na verdade, isso não separa
   porque..."), mas **sem virar teatro** (não inventar dúvida artificial num problema que
   não tem ambiguidade real — mesma regra de "não force pegadinha onde não há" que já vale
   pro resto do dataset).
2. **Depois do `</think>`: a resposta final, mais enxuta que o texto original.** Como a
   deliberação já foi feita no `<think>`, o texto visível não precisa reargumentar do zero —
   vira: passos de execução em LaTeX (linha a linha, isso continua obrigatório — regra 3 de
   `generator_math_gpt56.md` não muda), verificação cruzada, resposta em `\boxed{}`. Pode ser
   mais curto que a versão atual do item porque a parte deliberativa "por que essa técnica"
   já não precisa estar em prosa antes da execução — ela já aconteceu no `<think>`.

Regra dura: **o conteúdo matemático não pode mudar.** Mesma técnica, mesmo resultado, mesmo
valor final. Isso é retrofit de formato, não uma nova tentativa de resolver o problema — se
o GPT-5.6 "resolver de novo" e chegar num caminho diferente, pare e confira contra o item
original antes de aceitar.

## Variação obrigatória (mesma lição do documento-irmão)

`generator_math_gpt56.md` já registrou o bug de frase-fôrma (50/50 itens abrindo com a
mesma frase). Isso vale igual ou pior aqui: se os 34 itens abrirem o `<think>` sempre com
"Antes de aplicar [técnica], preciso confirmar..." ou fecharem sempre com a mesma transição
pro `</think>`, é o mesmíssimo problema, só que agora dentro de um bloco que carrega loss.
Peça variedade real de abertura/fechamento do `<think>` — não uma fórmula fixa reaproveitada
com o assunto trocado.

## Formato de saída

Devolva o objeto JSON **completo e válido**, mesmo schema de entrada
(`layer`, `lang`, `messages`, `_task` preservados), só com o(s) `content` de turno
`assistant` reescritos conforme acima. Uma linha por item, sem markdown ao redor, mesma
convenção de sempre (sem crase tripla, sem texto antes/depois do JSON). Se o item original
tiver `<tool_call>` no meio da conversa (turno assistant seguido de `tool`), o `<think>`
desse turno específico cobre só a deliberação até a decisão de chamar a tool — nunca dentro
da tag `<tool_call>` — e, se houver um turno `assistant` final depois do resultado da tool,
ele pode ter seu próprio `<think>` menor (avaliar se o resultado bate com o esperado) antes
da resposta final.

## Checklist antes de aceitar a edição

1. Resultado matemático idêntico ao item original (mesma técnica, mesmo valor, mesmo
   `\boxed{}`).
2. `<think>` contém deliberação genuína (por que não a abordagem óbvia / dificuldade real /
   escolha entre técnicas) — não é o texto visível antigo só copiado pra dentro da tag.
3. Texto visível pós-`</think>` ainda mostra a álgebra linha a linha (não virou resumo em
   prosa só porque a deliberação saiu de lá).
4. `<tool_call>`, quando existir, está fora do `<think>`, formato nativo intacto.
5. Sem abertura/fechamento de `<think>` repetida verbatim entre os itens do lote.
6. JSON válido, uma linha, schema idêntico ao original fora do campo `content`.

## Onde isso vira dataset de verdade

1. Você recebe o JSONL editado do GPT-5.6, item por item ou em lote.
2. Eu confiro cada um contra o checklist acima.
3. Os aprovados substituem a versão sem `<think>` correspondente em
   `data/raw/gpt56_<família>.jsonl` (mesmo arquivo, mesmo `_task.task_id` — é edição, não
   um item novo).
4. Rodo `python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl
   data/raw/gpt56_combined_selection.jsonl` de novo (ou os arquivos de família relevantes)
   pra regenerar `data/clean/dataset.jsonl` deste branch.
5. Confirmo pelos testes de `preamble_text()` que `<think>...</think>` não entra na
   medição antes de rodar `eval_harness.py`; assim a métrica continua comparável com o
   branch `main`.
