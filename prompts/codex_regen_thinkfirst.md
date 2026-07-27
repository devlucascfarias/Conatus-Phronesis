# Mega-prompt para Codex (GPT-5.6, raciocínio xhigh) — regeneração think-first das 7 famílias pendentes

Cole este arquivo inteiro como prompt no Codex, com o repositório `phronesis-thinking`
aberto. Ele é autocontido: define a tarefa, as regras duras, o formato de saída e o
autoteste. Não precisa de conversa de ida e volta.

---

## 0. Contexto mínimo — por que esta tarefa existe

Este repositório treina o **Conatus Phronesis**: um `Qwen/Qwen3-8B` (QLoRA) que decide
quando buscar na web, quando verificar num sandbox Python e quando só responder. O branch
`phronesis-thinking` adiciona um bloco `<think>` nativo do Qwen3 a cada turno do assistant.

Uma auditoria (2026-07-26) encontrou o defeito central do dataset atual: os blocos
`<think>` das camadas de computação têm **mediana de 18–21 palavras** — são uma *legenda*
da resposta, não o raciocínio que a produziu. Isso aconteceu porque foram criados por
**retrofit**: pegava-se um item já resolvido e pedia-se um `<think>` depois. Um raciocínio
escrito depois da resposta não pode tê-la produzido; só a descreve.

O efeito medido no modelo treinado foi grave: ele aprendeu a **suprimir** o mecanismo de
reasoning nativo do Qwen3-8B (que gera centenas a milhares de tokens em problemas
difíceis). Comparado ao `qwen3:8b` base, sem adapter, na mesma bateria de 9 perguntas, o
modelo treinado regrediu — errou aritmética que o base acerta, fabricou placares e fontes
que o base recusa educadamente, e colapsou em loop de repetição.

**Sua tarefa corrige a raiz disso.** Você vai resolver 350 problemas **do zero**, com o
`<think>` acontecendo *antes* de você saber a resposta.

O método já foi validado neste repositório: a família `limites` foi regenerada assim e
saiu com `<think>` de mediana 31 palavras (camada 2) e 82 palavras (camada 3), com
deliberação genuína. As outras 7 famílias ainda estão no formato antigo e são o alvo aqui.

---

## 1. A regra que governa tudo

> **Você recebe SÓ o enunciado. Resolve do zero. O `<think>` é o raciocínio que acontece
> ANTES de saber a resposta; a resposta é o que sai desse raciocínio.**

Consequências que não são negociáveis:

- **Se você chegar a um resultado errado, o item é DESCARTADO — não corrigido.** Isso é
  *rejection sampling*, e é o mecanismo inteiro. Um `<think>` que leva ao resultado errado
  é exatamente o que nunca queremos ensinar. Um `<think>` que leva ao certo é causal por
  ter sido gerado antes da resposta. **Nunca "conserte a resposta mantendo o think"** —
  isso reintroduz o pós-hoc que estamos eliminando.
- Marque itens descartados explicitamente (seção 7). Descartar é resultado válido e
  esperado; entregar 50/50 em toda família é sinal de que algo foi forçado.

### Proibição de contaminação (leia com atenção)

Os arquivos `data/raw/gpt56_*.jsonl` contêm as **soluções antigas** destes mesmos
enunciados. **NÃO ABRA ESSES ARQUIVOS.** Ler a solução antiga antes de resolver destrói o
propósito da tarefa: seu `<think>` viraria racionalização de uma resposta que você já viu,
que é precisamente o defeito sendo corrigido.

Seus insumos são **exclusivamente** os arquivos de `data/raw/enunciados_pendentes/`, que
contêm só o enunciado, o índice e a camada. Foram preparados para isto.

Exceção única: `data/raw/gpt56_limites.jsonl` **pode** ser lido como referência de
*estilo* — é a família já regenerada think-first, o padrão de qualidade a igualar. Use para
calibrar tom e profundidade, nunca para copiar conteúdo (é outro assunto matemático).

---

## 2. O teste central: o `<think>` tem que ser *load-bearing*

Antes de aceitar qualquer item, aplique o **teste contrafactual**:

> Se eu apagar o bloco `<think>`, a resposta visível fica sem justificativa para pelo menos
> UMA escolha (qual método, por que a forma não é indeterminada, por que a abordagem óbvia
> falha)? Se a resposta se sustenta inteira sozinha, o `<think>` é decorativo — **rejeite**.

Um `<think>` load-bearing contém pelo menos um destes, e a resposta visível **depende**
dele em vez de re-derivá-lo:

- **por que a abordagem ingênua não serve** (ex.: "termo a termo não vale aqui porque a
  convergência não é uniforme — preciso de convergência dominada"), decidido *antes* de
  qualquer linha de LaTeX da execução;
- **qual é a dificuldade real** antes de resolver (o que especificamente impede a solução
  trivial);
- **a escolha genuína entre duas técnicas plausíveis** — comparando as duas, não só
  anunciando a vencedora;
- **a verificação da forma** (substituir direto no ponto: é mesmo `0/0`, `∞/∞`, `0·∞`? ou a
  "indeterminação" é falsa e resolve por continuidade?).

### Deliberação real ≠ teatro

O risco oposto ao pós-hoc é inventar dúvida onde não há:

- Problema **sem armadilha** tem think **curto** — uma frase de deliberação genuína basta.
  Não infle para bater um número de palavras.
- Não force "caminho abandonado" num problema sem bifurcação real. Beco-sem-saída só entra
  quando o problema genuinamente induz a um — e aí **deixe o beco no think** (foi o que
  aconteceu ao resolver), em vez de apagá-lo para deixar limpo.
- A extensão segue a dificuldade real. Se um problema de camada 3 for genuinamente direto
  pra você, um think de 60 palavras honesto é melhor que 200 de enchimento.

---

## 3. Pisos de comprimento (verificados por script — não são sugestão)

`src/validate_data.py` **rejeita mecanicamente** itens fora destes limites:

| Camada | `think_min_words` | `think_max_words` |
|---|---|---|
| 2 | **30** | sem teto |
| 3 | **60** | sem teto |

Estes pisos existem porque o retrofit produzia 18–21 palavras. Eles são um piso de
segurança, **não uma meta** — não escreva para o contador. Se a deliberação honesta de um
item de camada 2 tem 28 palavras, o problema é fácil demais para a camada: **descarte o
item** (seção 7) em vez de inflar o think com enchimento. Inflar é exatamente o teatro que
a seção 2 proíbe, e passa no script enquanto envenena o treino.

Referência de calibração da família `limites` já aprovada: camada 2 mediana 31 (faixa
13–37), camada 3 mediana 82 (faixa 63–113).

---

## 4. Estrutura de cada item

O `content` do turno `assistant` é **literalmente**:

```
<think>
<deliberação>
</think>

<resposta visível>
```

**Dentro do `<think>` — deliberação, estilo cru, pensando alto:**
- verificação da forma → dificuldade real → escolha de método justificada;
- frases mais curtas e diretas que a prosa técnica final; reconsiderações explícitas quando
  reais ("na verdade isso não separa porque…");
- **sem `<tool_call>` dentro** — a decisão de chamar a tool pode ser deliberada aqui, mas a
  tag em si vem depois do `</think>`.

**Depois do `</think>` — execução limpa:**
- a álgebra/cálculo **linha a linha em LaTeX** (obrigatório — a deliberação ter saído pro
  think não dispensa mostrar a conta sendo feita; proibido pular de "aplicando X" pro
  resultado);
- verificação cruzada por caminho independente do usado na execução (método alternativo,
  substituição numérica, caso-limite, análise dimensional em física, ou `python_sandbox`);
- resposta final única em `\boxed{}` quando couber.

Como o "por que essa técnica" já aconteceu no think, o texto visível **não reargumenta a
escolha do zero** — ele executa. É assim que se vê que o think carrega peso.

---

## 5. Itens com `python_sandbox`

**Invariante do projeto: nunca fabricar stdout.** O validador reexecuta todo código e
compara com o turno `tool`.

Quando o item usa sandbox, o turno `assistant` **termina no `<tool_call>`** e o objeto JSON
leva `"_needs_execution": true`. O Lucas executa de verdade e completa o episódio (turno
`tool` real + `<think>` curto de avaliação + resposta final). **Não escreva o turno `tool`
nem a resposta final desses itens.**

Formato nativo Qwen3, exato:

```
<tool_call>
{"name": "python_sandbox", "arguments": {"code": "...print(resultado)"}}
</tool_call>
```

Regras duras:
- **`python_sandbox` é o único nome de tool válido** para cálculo. O modelo treinado
  alucinou `python_sandro`, `python_jupyter_cell`, `python_eval`, `python` — nunca escreva
  variação nenhuma.
- O código precisa calcular **a quantidade do problema** (não uma expressão qualquer que
  roda) e terminar em `print()`.
- Imports permitidos no sandbox: `math`, `numpy`, `sympy`, `statistics`, `itertools`,
  `fractions`, `decimal`. **Sem rede, sem `requests`, sem `input()`, sem I/O de arquivo.**
  Timeout de 5 s.
- Só use sandbox onde ele agrega. Não force em problema que se verifica por álgebra pura.
  Em `fisica_computacional` é o oposto: quase todo item usa, é o ponto da família.

---

## 6. Regras de formato (todas verificadas mecanicamente)

- **`<think>` no início absoluto do `content`**, precedido de nada. Regex do validador:
  `\A<think>\n(.*?)\n</think>(\n\n(.*))?\Z`. Uma quebra de linha depois de `<think>`, uma
  antes de `</think>`, e exatamente `\n\n` antes da resposta visível.
- Nunca `<think>` sem `</think>`; nunca aninhar; nunca `<tool_call>` dentro do think.
- **Só LaTeX** para expressão matemática — nada de unicode solto (`∛`, `²`, `→`, `≤`)
  misturado. Use `\sqrt[3]{}`, `\frac{}{}`, `\lim\limits`, `\displaystyle`, `\leq`.
- **Idioma: o `<think>` segue o `lang` do item, sempre.** Auditoria achou 7,7% dos blocos
  atuais em inglês num dataset pt-BR — contaminação real que degradou a fluência do modelo.
  Item `pt-BR` pensa em português; item `en` pensa em inglês. Nunca misture no mesmo item.
- Sem markdown de chat: sem "Aqui está a resolução:", sem `---`, sem emoji, sem headers
  `#`/`##` dentro do turno.
- **Anti-frase-fôrma** (o validador conta 6-gramas, `ngram_max_freq: 3`): a abertura do
  `<think>` e a conectiva de verificação cruzada não podem repetir mais de ~3 vezes por
  lote. Num lote de 50, quero **pelo menos 15 aberturas distintas**. O bug histórico foi
  50/50 itens abrindo com "Verificação da forma:" — não repita a lição.
- Gírias banidas: `mano`, `véi`, `vei`, `top demais`, `brabo`, `braba`, `cringe`,
  `tipo assim`.
- O item renderizado precisa caber em **4096 tokens** no tokenizer do Qwen3-8B. Camada 3
  longa cabe folgada; só não escreva uma monografia.

---

## 7. Formato de saída

Uma família por arquivo, em `data/raw/gpt56_<família>.jsonl`, **sobrescrevendo** o
antigo — é substituição, não acréscimo.

**Preserve `idx`, `layer` e `lang` do arquivo de enunciados, na mesma ordem.** Isso não é
cosmético: `src/build_gpt56_selection.py` e `src/build_math_rigor_testset.py` fatiam por
**posição** (`camada2[0:3]` e `camada3[4:6]` são held-out; `camada2[3:]` e `camada3[0:2]`
são treino). Mudar a ordem ou a contagem por camada quebra o split e vaza avaliação para
dentro do treino.

Schema, uma linha por item, sem `idx` no objeto final:

```json
{"layer": "3", "lang": "pt-BR", "messages": [{"role": "user", "content": "<enunciado literal, inalterado>"}, {"role": "assistant", "content": "<think>\n...\n</think>\n\n<execução + verificação + \\boxed{}>"}]}
```

Com sandbox:

```json
{"layer": "2", "lang": "pt-BR", "_needs_execution": true, "messages": [{"role": "user", "content": "<enunciado>"}, {"role": "assistant", "content": "<think>\n...\n</think>\n\n<preâmbulo curto>\n<tool_call>\n{\"name\": \"python_sandbox\", \"arguments\": {\"code\": \"...\"}}\n</tool_call>"}]}
```

- O enunciado do turno `user` é copiado **literalmente**, sem paráfrase nem correção.
- JSONL puro: uma linha = um objeto. Sem crase tripla, sem `[...]` envolvendo, sem vírgula
  entre linhas, sem texto antes ou depois.
- Escape correto dentro das strings JSON: LaTeX `\` vira `\\`, aspas viram `\"`.

**Itens descartados** (você chegou a resultado errado, ou o problema não sustenta a
deliberação mínima da camada): **não** entram no `.jsonl`. Registre-os em
`data/raw/enunciados_pendentes/<família>_descartados.md`, com o `idx`, o enunciado e uma
frase dizendo por quê. Um arquivo por família, mesmo que vazio.

---

## 8. Ordem de trabalho

Uma família por vez, fechando cada uma antes de abrir a próxima:

1. `algebra_linear`
2. `analise_complexa`
3. `equacoes_diferenciais`
4. `fisica1`
5. `fisica2`
6. `fisica_computacional`
7. `matematica_fisica`

São 50 itens por família, 350 no total. Resolva em blocos de 12–15 para manter a qualidade
do raciocínio estável — mas entregue o arquivo da família completo antes de passar adiante.

---

## 9. Autoteste antes de fechar cada família

Rode e reporte a saída:

```bash
python src/validate_data.py data/raw/gpt56_<família>.jsonl
```

Ele checa mecanicamente: formato do `<think>`, pisos de 30/60 palavras, `<tool_call>` fora
do bloco, schema da tool, execução real do sandbox, eco do stdout na resposta, gíria,
frase-fôrma e dedup. **Itens rejeitados aparecem em `data/clean/rejected.jsonl` com o
motivo** — leia e corrija de verdade (regenerando o item do zero, nunca remendando o
think).

Depois, confira você mesmo, item a item:

1. **Contrafactual**: apagando o `<think>`, a resposta fica sem justificativa para ao menos
   uma escolha? Se não, o think é decorativo.
2. **Ordem**: a deliberação está no `<think>`, ANTES da execução — não colada depois do
   `\boxed{}` como justificativa retroativa.
3. **Resultado correto**, resolvido do zero. Se o think leva ao valor errado, o item foi
   descartado (não consertado)?
4. Execução visível linha a linha em LaTeX — não virou resumo em prosa.
5. Zero contradição entre `<think>`, execução, checker e resposta final.
6. Se há sandbox: `_needs_execution: true`, turno termina no `</tool_call>`, nome da tool é
   exatamente `python_sandbox`, código calcula a quantidade do problema.
7. `lang` do think bate com o `lang` do item.
8. ≥15 aberturas de `<think>` distintas no lote de 50.
9. `idx`/`layer`/ordem preservados em relação ao arquivo de enunciados.

Ao fechar cada família, reporte: quantos itens entregues, quantos descartados e por quê, a
mediana de palavras do `<think>` por camada, e a saída do validador.
