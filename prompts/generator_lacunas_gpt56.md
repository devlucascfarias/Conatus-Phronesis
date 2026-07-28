# Brief para o GPT-5.6 (raciocínio xhigh) — lote corretivo de lacunas estruturais

Este arquivo é para ser colado como instrução (system ou primeira mensagem) numa conversa com o
GPT-5.6 em modo de raciocínio estendido. Ele **não** substitui `prompts/generator_math_gpt56.md`
nem `prompts/generator_system.md` — pressupõe os dois. O que vem aqui é o lote seguinte, dirigido
a lacunas que uma auditoria completa do repositório (2026-07-27) mostrou serem **estruturais do
corpus**, não erros de geração pontuais.

A diferença de intenção em relação aos briefs anteriores: os lotes 001–032 corrigiram *erros
observados*, um a um, gerando mais exemplos do comportamento certo. Este lote corrige *ausências* —
comportamentos que o corpus nunca demonstra em nenhum exemplo, e que por isso o modelo pequeno
resolve caindo no prior do modelo-base (Qwen3), que é onde nascem os defeitos abaixo.

---

## Estado do corpus na data deste brief

Números medidos em `data/clean/dataset.jsonl` (901 exemplos aprovados de 1181 gerados):

| Camada | n | share | alvo | com `python_sandbox` | com `web_search` |
|---|---|---|---|---|---|
| 0 | 104 | 0,115 | 0,20 | 0 | 0 |
| 0.5 | 95 | 0,105 | 0,12 | 0 | 0 |
| 1 | 288 | 0,320 | 0,25 | 0 | 287 |
| 2 | 221 | 0,245 | 0,18 | **97** | 0 |
| 3 | 56 | 0,062 | 0,05 | 28 | 15 |
| C | 137 | 0,152 | 0,20 | 0 | 0 |

Blocos de código de sandbox no corpus inteiro: **142**. Todos executam, todos imprimem com
`print()`, nenhum usa `input()`, nenhum usa rede ou I/O de arquivo. O código do corpus está limpo —
o problema não é dado ruim, é dado ausente e dado escasso.

---

## Lacuna 1 — o corpus só mostra o caminho feliz da tool call

### Evidência

O modelo em produção inventa nome de ferramenta e escreve código quebrado. Nomes inventados já
registrados em `data/eval/thinking_8b_eval_notes.md`: `python`, `python_jupyter_cell`,
`python_print`, `python_eval`, `python_sandro`, `python_sandox` — seis variantes distintas. Código
com string não fechada apareceu duas vezes seguidas no mesmo item (item 2 da rodada de sampling),
e o modelo nunca entregou a função pedida.

E o caso mais diagnóstico de todos, medido ao vivo em 2026-07-27 contra o enunciado
`Calcule 62,5% de 4.960`:

```python
base = 4960
percentual = float(input('Percentual? '))
print(round(base * percentual / 100, 3))
```

→ `EOFError: EOF when reading a line`, e o modelo desistiu dizendo "faltou passar o número que
representa os 62,5%" — sendo que o número está no enunciado que ele acabou de ler.

Esse enunciado **existe no corpus de treino**, com a resposta certa:

```python
base = 4960
print(5*base/8)
```

Ou seja: o modelo reproduziu o literal memorizado (`base = 4960`) e então **trocou a parte
específica do problema por um parâmetro genérico lido de fora**. Não é falta de generalização
para enunciado novo — é contaminação do prior de "script Python parametrizado" sobre um exemplo
que ele viu literalmente no treino. Com 142 blocos de código no corpus inteiro, o sinal do
fine-tune é fino demais para vencer esse prior.

### O que o corpus nunca mostra

Não existe **nenhum** exemplo em que o modelo:
- chama uma ferramenta com nome errado, recebe o erro, e se recupera chamando o nome certo;
- escreve código que falha por sintaxe (não por lógica), lê o `SyntaxError`, e reescreve;
- escreve código que tenta ler de fora (`input()`, `open()`, `requests`), recebe o erro, e
  reescreve embutindo o literal que já estava no enunciado;
- é explicitamente instruído, no próprio raciocínio, de que todo valor do problema entra no código
  como literal.

Os episódios de traceback do `batch_027` cobrem erro de *lógica/runtime*, não essa classe.

### O que gerar — família A: recuperação de falha de ferramenta

**40 exemplos, camada 2** (alguns podem ser 3 se o problema por baixo for difícil), distribuídos:

- **15 itens `input()`/entrada externa.** O primeiro `python_sandbox` do turno usa `input()`,
  `sys.argv`, `open()` ou `requests.get()` para obter um valor que **já está no enunciado**. O turno
  `tool` traz o traceback real (`EOFError: EOF when reading a line`, `FileNotFoundError`,
  `ModuleNotFoundError: No module named 'requests'` — o sandbox não tem rede). O `<think>` seguinte
  nomeia o erro de raciocínio com precisão — *o valor estava no enunciado; parametrizar foi o
  erro, não a conta* — e o segundo `python_sandbox` embute o literal e fecha.
- **10 itens de nome de ferramenta inválido.** A primeira `<tool_call>` usa um nome que não existe
  (`python`, `python_eval`, `run_python`, `calculator`, `python_sandox`). O turno `tool` responde
  com o erro de ferramenta desconhecida — use exatamente este formato, que é o que
  `src/inference_loop.py` produz de verdade:
  `{"error": "tool desconhecida: python_eval", "available": ["web_search", "python_sandbox"]}`.
  O `<think>` seguinte reconhece em uma frase e reemite com `python_sandbox`, **sem reescrever o
  código** (o código estava certo; só o nome estava errado — a correção tem que ser cirúrgica, não
  uma refação do zero).
- **10 itens de erro de sintaxe.** String não fechada, parêntese faltando, indentação inválida,
  f-string malformada. Traceback real (`SyntaxError: unterminated string literal (detected at line
  1)`), correção mínima, resultado.
- **5 itens de import indisponível.** O código usa `scipy`, `pandas` ou `matplotlib` (o sandbox só
  tem `math`, `numpy`, `sympy`). `ModuleNotFoundError` real, e a reescrita resolve o mesmo problema
  com o que existe — mostrando que a restrição não impede a resposta, só muda o caminho.

**Regra dura desta família**: o erro tem de ser **plausível como erro do modelo pequeno**, não uma
pegadinha artificial. Nada de erro rebuscado que ninguém cometeria. E o segundo código tem de ser
uma edição *mínima* do primeiro sempre que isso for verdade — ensinar reescrita total ensina o
modelo a jogar fora trabalho correto.

**Regra dura nº 2**: no máximo **duas** tentativas. Se o segundo código também falhasse, o exemplo
vira desistência graciosa (ver Lacuna 4) — nunca uma terceira tentativa. O corpus não pode ensinar
retry ilimitado, que é exatamente o colapso em loop já medido.

### O que gerar — família B: a regra positiva, dita explicitamente

**15 exemplos, camada 2, sem erro nenhum.** Cálculo de rotina resolvido de primeira, mas onde o
bloco `<think>` **verbaliza a restrição** antes de escrever o código, com formulação variada
(mínimo 10 redações distintas, sem frase-fôrma):

> "Os dois valores estão no enunciado, então entram como literais — código de sandbox não tem de
> onde ler nada."

> "Sem entrada externa: 4.960 e 5/8 vão escritos no código, que só imprime o resultado."

Isso dá ao fine-tune um sinal *positivo* da regra, não só a correção depois do erro. Distribua os
enunciados por tipo de grandeza — porcentagem, juros compostos, conversão de unidade, média
ponderada, regra de três, escala/proporção — porque a família de porcentagem é justamente onde o
defeito reincide.

---

## Lacuna 2 — a camada 2 ensina duas políticas opostas sob o mesmo rótulo

### Evidência

Dos 221 exemplos de camada 2, **97 chamam `python_sandbox` e 124 não chamam ferramenta nenhuma** —
esses 124 são a distilação de matemática do GPT-5.6, resolvida analiticamente em LaTeX. Os dois
grupos são internamente corretos. O problema é que, para uma pergunta de cálculo, o corpus
demonstra dois comportamentos incompatíveis **sem que nada no input diferencie os casos**.

O efeito medido é exatamente o esperado de um sinal ambíguo: em produção o modelo às vezes vai
direto ao `\boxed{}` sem verificar (itens 7, 11 e 15 da rodada de sampling erraram assim, "errado
com confiança"), e às vezes chama o sandbox para uma conta que não precisava — e quebra o código
no caminho, que é o caso de 62,5%.

O `batch_030` já atacou uma metade disso ("fórmula de cor ainda passa pelo sandbox"). O que falta é
a **fronteira**: exemplos que digam, no raciocínio, por que *este* problema dispensa o checker e
aquele não.

### O que gerar — família C: pares contrastivos de decisão de verificação

**30 exemplos, em 15 pares.** Cada par tem dois enunciados **da mesma família matemática e de
dificuldade parecida**, em que:

- o item **sem sandbox** é verificável por álgebra exata — identidade fechada, cancelamento
  simbólico, resultado inteiro por construção, checagem dimensional que fecha sozinha;
- o item **com sandbox** tem um ponto onde o erro humano/de modelo é real e silencioso — aritmética
  de várias casas decimais, potência/raiz não exata, soma de série truncada, conversão de unidade
  com fator não redondo, expressão longa o suficiente para um sinal se perder.

O `<think>` de **cada um dos dois** tem de nomear a propriedade que decidiu, e as duas frases têm
de ser reconhecivelmente simétricas — "o resultado fecha por identidade, conferir numericamente não
acrescenta informação" contra "a conta tem cinco casas e um expoente fracionário; é onde eu erraria
sem perceber". Não é o assunto que decide; é a **falibilidade da conta específica**.

Não gere os dois itens do par com números parecidos — o par existe no nível da lição, não do
enunciado. Se ficarem parecidos demais, o dedup por Jaccard (`0.80` em `configs/gen_config.yaml`)
descarta um dos dois.

---

## Lacuna 3 — instrução de formato do usuário não altera a resposta

### Evidência

`prompts/generator_math_gpt56.md` já documenta o bug ("surdez a instrução explícita de formato"):
pedido de "mostre o passo a passo" na segunda mensagem produziu a mesma resposta *word-by-word*.
A auditoria mostra por que ele nunca foi corrigido: **de 901 exemplos, apenas 14 estão marcados
`multi_turn: true`** (alvo em `gen_config.yaml`: 0,25 — ou seja, ~225). Toda a distilação de
matemática do GPT-5.6 é de turno único. O corpus praticamente não contém segundo turno de usuário,
e **nenhum** contém um segundo turno que peça *outra forma da mesma resposta*.

### O que gerar — família D: refazer sob nova instrução

**25 exemplos, camadas 2 e 3, todos multi-turno.** Estrutura: `user` → `assistant` (resposta
correta e completa no registro pedido) → `user` pede uma **transformação de formato** → `assistant`
entrega algo visivelmente diferente, com a mesma matemática.

Transformações a variar entre os itens:
- "mostra o passo a passo" → a segunda resposta é substancialmente mais longa, cada manipulação
  algébrica em sua própria linha de LaTeX;
- "resume, só o resultado" → segunda resposta curta, sem derivação, sem repetir o preâmbulo;
- "explica como se eu não soubesse cálculo" → mesma conta, vocabulário e analogia mudados, rigor
  preservado;
- "e se fosse [variação do parâmetro]?" → refaz com o novo valor, **sem recopiar** a derivação
  inteira: aproveita o que não mudou e diz o que mudou;
- "confere isso pra mim" → agora sim chama `python_sandbox` sobre um resultado que a primeira
  resposta deu sem checker.

**O ponto que o exemplo tem de provar**: a segunda resposta não pode ser a primeira com uma frase
a mais. Se as duas respostas do exemplo compartilham a maior parte do texto, o exemplo está errado
e não ensina nada — refaça. O `<think>` do segundo turno deve nomear a mudança pedida
("ele já tem o resultado; o que falta é a álgebra visível, então a derivação vira o corpo da
resposta e a conclusão encolhe").

---

## Lacuna 4 — desistência graciosa existe, mas não sob falha de ferramenta

`batch_023`/`batch_024` cobriram desistência graciosa. A auditoria de
`thinking_8b_eval_notes.md` mostra que o colapso restante acontece num contexto específico que
esses lotes não cobrem: **quando é a ferramenta que falha repetidamente**, não o raciocínio.

### O que gerar — família E

**10 exemplos, camadas 2 e 3.** Duas tentativas de `python_sandbox` falham por motivos
*diferentes* (não a mesma falha duas vezes — isso é o loop que queremos evitar). Na terceira, o
assistente **para**, e entrega:

1. o que ele conseguiu estabelecer sem o checker (a montagem do problema, a fórmula, o valor
   analítico quando houver);
2. a ressalva explícita e específica sobre o que ficou sem verificação — não um hedge genérico:
   "a conta simbólica fecha; o que não consegui confirmar foi o valor numérico de {expressão}";
3. **nenhuma** terceira tentativa, nenhuma reabertura, nenhum pedido de desculpa repetido.

O tom é o mesmo já estabelecido para autocorreção: reconhece em uma frase e segue. Sem
autoflagelação, sem oferecer cinco alternativas.

---

## Lacuna 5 — alucinação de unidade e mistura de idioma

Dois defeitos pequenos, ambos com evidência e ambos baratos de corrigir por volume.

**Unidade fabricada**: "R$" aparece em resposta de porcentagem cujo enunciado não menciona dinheiro
— 2 de 2 casos testados, apesar do contraste do `batch_022`. O corpus tem o contraste, mas em
volume insuficiente.

**Mistura de idioma**: o Qwen3-8B base, testado nos mesmos 9 enunciados em 2026-07-27, respondeu
`62,5% de 4.960` **em espanhol** ("seguimos estos pasos", "Multiplicar por el valor total") a partir
de um enunciado em português. É defeito do modelo-base, e o corpus atual (767 pt-BR / 134 en, nunca
misturados dentro do mesmo exemplo) confia em nunca mostrar o erro para ensiná-lo — o que a Lacuna 1
já mostrou não bastar contra um prior forte.

### O que gerar — família F

**20 exemplos, camadas 0/0.5/2**, metade e metade:

- **10 de disciplina de unidade**: pares em que o *mesmo* número sai com unidade e sem unidade
  conforme o enunciado. "Quanto é 15% de 300?" → `45`, número puro; "Quanto é 15% de R$ 300?" →
  `R$ 45,00`; "Quanto é 15% de 300 km?" → `45 km`. O `<think>` diz explicitamente que a grandeza
  vem do enunciado e não é presumida. Varie a grandeza: moeda, distância, massa, tempo, dados
  (GB), população, temperatura.
- **10 de ancoragem de idioma**, sendo 6 pt-BR e 4 en: enunciado com termo técnico estrangeiro,
  nome próprio ou notação que puxaria o modelo para o outro idioma (`eigenvalue`, `input`,
  `throughput`, `Runge-Kutta`, `steady-state`, nome de autor). A resposta inteira permanece no
  idioma do enunciado — o termo técnico pode ficar no original, mas **nenhuma frase de estrutura**
  ("seguimos los siguientes pasos", "let's calculate") muda de idioma. Nunca há troca de idioma no
  meio da resposta, nem mesmo em uma palavra funcional.

---

## Balanceamento — o lote tem de puxar as camadas de volta ao alvo

As camadas 0 (0,115 contra alvo 0,20) e C (0,152 contra 0,20) estão bem abaixo do alvo, e a
camada 1 (0,320 contra 0,25) bem acima. O histórico do `GEN_PROGRESS.md` mostra que já houve
regressão de coerência conversacional exatamente quando C caiu (`batch_014`) — o desequilíbrio
atual é maior do que aquele.

### O que gerar — família G

**30 exemplos, sendo 18 de camada 0 e 12 de camada C.** Sem tool, sem cálculo.

- Camada 0: fato estável, definição, pergunta factual simples. Resposta seca, preâmbulo **zero**,
  `<think>` de no máximo 15 palavras. Temas frescos, fora do `data/eval/testset.jsonl`.
- Camada C: conversa — desabafo, comemoração, nostalgia, opinião, criatividade curta, pergunta
  pessoal ao assistente. Tom natural, sem estrutura de laudo. Onde houver fato, ele tem de ser
  **verdadeiro e verificável** (regra do `batch_015`; o modelo já inventou fato nesse contexto).

Um alerta específico para a camada C, medido na comparação de 2026-07-27: o modelo produziu, sobre
polígonos regulares, a afirmação de que "hexágonos são os **únicos** polígonos regulares que
pavimentam o plano" — falso (triângulo equilátero e quadrado também pavimentam), e no mesmo
parágrafo mencionou "cascas de melancia" formando esse padrão, o que não existe. Curiosidade de
camada C não é licença para afrouxar a verdade: se o fato tem uma condição de unicidade, ou ela é
verdadeira ou a frase não entra.

---

## Total do lote e ordem de geração

| Família | Tema | n | Camadas |
|---|---|---|---|
| A | Recuperação de falha de ferramenta | 40 | 2, 3 |
| B | Regra positiva "literal no código" | 15 | 2 |
| C | Pares contrastivos de decisão de verificação | 30 | 2 |
| D | Refazer sob nova instrução (multi-turno) | 25 | 2, 3 |
| E | Desistência graciosa sob falha de ferramenta | 10 | 2, 3 |
| F | Unidade e ancoragem de idioma | 20 | 0, 0.5, 2 |
| G | Rebalanceamento | 30 | 0, C |
| | **Total** | **170** | |

Ordem sugerida: **A → B → C → E → D → F → G**. A e B primeiro porque são o defeito que quebra
respostas inteiras hoje; G por último porque é volume e não depende de nada.

Por rodada de chat com o GPT-5.6: 12–15 exemplos de uma família por vez, como já se faz nas
famílias de matemática.

---

## Formato de saída — idêntico aos lotes anteriores

Uma linha JSON por exemplo, sem markdown em volta:

```json
{"layer": "2", "lang": "pt-BR", "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "<think>\n...\n</think>\n\n...\n<tool_call>\n{\"name\": \"python_sandbox\", \"arguments\": {\"code\": \"...\"}}\n</tool_call>"}, {"role": "tool", "content": "<stdout ou traceback REAL>"}, {"role": "assistant", "content": "<think>\n...\n</think>\n\n..."}]}
```

Diferença importante em relação a `generator_math_gpt56.md`: **aqui o `<think>` é obrigatório** em
todo turno de assistant. Aquele brief o proibia porque a distilação de matemática passava por um
editor posterior (`prompts/editor_thinking_gpt56.md`) que inseria o bloco — e
`configs/gen_config.yaml` documenta que esse retrofit produziu "legenda da resposta" em vez de
deliberação, o que motivou o piso `think_min_words`. Este lote nasce think-first: escreva o
raciocínio antes de saber a resposta final, não depois.

Tetos e pisos de `<think>` por camada, que o validador cobra:

| Camada | Preâmbulo visível | `<think>` |
|---|---|---|
| 0 | 0 palavras (e zero tool call) | ≤ 15 palavras |
| 0.5 | ≤ 25 palavras | ≤ 25 palavras |
| 1 | ≤ 40 palavras | ≤ 35 palavras |
| 2 | — | **≥ 25 palavras** |
| 3 | — | **≥ 60 palavras** |
| C | — | ≤ 20 palavras |

O piso das camadas 2/3 vale para os turnos de **deliberação** (os que decidem o caminho). O turno
de assistant que vem logo depois de um `tool` avalia o resultado e pode ser curto — o validador
(`deliberation_turns` em `src/validate_data.py`) já isenta esse.

---

## Invariante inegociável: nada de stdout fabricado

`src/validate_data.py` **executa de verdade** todo `python_sandbox` das camadas 2 e 3
(`check_sandbox_execution`) e compara com o turno `tool`. Além disso, `check_answer_echoes_tool`
exige que o resultado reapareça na resposta final, e `check_websearch_grounding` exige que todo
número com casa decimal citado depois de uma busca exista nos resultados dela.

Consequências práticas para este lote, que tem erro deliberado no código:

- O traceback do turno `tool` tem de ser **o traceback real** daquele código, não uma paráfrase.
  Rode antes de escrever. Um `EOFError` inventado com a mensagem errada é reprovado.
- Quando o turno `tool` contém traceback, o validador exige que o código **de fato falhe** — um
  exemplo que afirma erro mas cujo código roda limpo é rejeitado com
  `tool_response_afirma_erro_mas_codigo_roda`.
- O segundo código, o que corrige, tem de rodar limpo e o stdout tem de bater com o número da
  resposta final, inclusive no arredondamento.

Antes de entregar o lote, rode:

```bash
python src/validate_data.py data/raw/gen/batch_0NN.jsonl
```

e leia `data/clean/report.json`. Um lote com rejeição acima de ~10% volta para reescrita em vez de
seguir para o merge.

---

## Checklist antes de aceitar cada exemplo

1. Todo turno de assistant tem `<think>`, dentro do teto/piso da camada.
2. O `<think>` delibera (decide o caminho antes de saber a resposta) — não descreve a resposta
   pronta. Se dá para colá-lo *depois* da resposta sem que o texto fique estranho, é legenda:
   refaça.
3. Onde há código, todo valor do enunciado entra como **literal**. Zero `input()`, `sys.argv`,
   `open()`, rede. Imports apenas de `math`, `numpy`, `sympy`.
4. Turnos `tool` contêm saída real, obtida executando o código.
5. No máximo duas tentativas de ferramenta por exemplo; a terceira é desistência graciosa.
6. A resposta final ecoa o número do stdout, com arredondamento explícito quando houver.
7. Unidade só aparece se o enunciado a introduziu.
8. Um idioma só, do começo ao fim, inclusive nas frases de estrutura.
9. Nenhuma frase de abertura ou transição se repete mais de 3 vezes no lote
   (`ngram_max_freq: 3`) — vale para as aberturas de `<think>` também.
10. Nenhum enunciado colide com `data/eval/testset.jsonl` ou
    `data/eval/math_rigor_testset.jsonl`. A auditoria encontrou 9 colisões exatas já existentes
    (entre elas "Quanto é 37,5% de 18.420?" e "Quanto tá o dólar hoje?"); não aumente o número.

---

## Nota sobre a origem deste brief

As lacunas acima vieram de uma auditoria de `data/clean/`, `src/`, `configs/` e
`data/eval/thinking_8b_eval_notes.md` feita em 2026-07-27, cruzada com uma comparação ao vivo entre
o `phronesis-4b` servido pelo Ollama e o `qwen3:8b` base nos mesmos 9 enunciados. O achado que
organiza o resto: **o corpus de treino está limpo** — 142 blocos de código, todos executáveis,
nenhum com `input()` — e ainda assim o defeito aparece em produção. Dado limpo não basta quando o
volume é fino e a regra nunca é dita; o prior do modelo-base preenche o silêncio. É por isso que
este lote pede tanto o erro-e-recuperação (família A) quanto a regra afirmada explicitamente
(família B), em vez de só mais exemplos corretos.
