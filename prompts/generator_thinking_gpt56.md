# Brief para o GPT-5.6 (raciocínio xhigh) — geração *think-first* de matemática/física

Este arquivo é a instrução (system ou primeira mensagem) numa conversa com o GPT-5.6 em
raciocínio estendido. Objetivo: gerar itens de treino das camadas 2 e 3 do Conatus
Phronesis **já com um bloco `<think>` de deliberação real**, resolvendo cada problema do
zero — não é reformatação de resposta pronta.

Alvo do branch `phronesis-thinking`: `Qwen/Qwen3-8B`, um modelo híbrido com mecanismo de
thinking de verdade. O GPT-5.6 escreve direto no schema `messages` final (uma linha JSON
por problema); ninguém reformata depois.

## Isto SUBSTITUI o retrofit — leia por quê

Existe um documento irmão, `editor_thinking_gpt56.md`, que pega uma resposta **já
resolvida e polida** e enxerta um `<think>` depois, com a regra dura de que "o resultado
matemático não pode mudar". **Não use aquele fluxo aqui.** Ele produz, por construção,
racionalização pós-hoc: se a resposta já está fixada antes do think existir, o think só
pode *justificar* uma conclusão pronta — nunca *derivá-la*. O resultado observado no modelo
treinado com esse método foi exatamente isso: traces que soam sensatos mas não carregam a
resposta (o think afirma um valor e a resposta visível diz outro; o think inventa hesitação
decorativa; passos do think que a resposta não usa).

Aqui a ordem é invertida e essa é a única coisa que importa:

> **O GPT-5.6 recebe SÓ o enunciado. Resolve do zero. O `<think>` é o raciocínio que
> acontece ANTES de saber a resposta; a resposta é o que sai desse raciocínio.**

Consequência prática que você (Lucas) aplica na curadoria: se o GPT-5.6, resolvendo
think-first, chegar num resultado **errado**, o item é **descartado**, não corrigido. Isso
é *rejection sampling*, e é o mecanismo — um think que leva ao resultado errado é justamente
o que a gente quer nunca ensinar; um think que leva ao certo é causal por ter sido gerado
antes da resposta. Nunca "conserte a resposta mantendo o think": isso reintroduz o pós-hoc.

## O teste central: o `<think>` tem que ser *load-bearing*

Antes de aceitar qualquer item, aplique o **teste contrafactual**:

> Se eu apagar o bloco `<think>`, a resposta visível fica sem justificativa para pelo menos
> UMA escolha (qual método, por que a forma não é indeterminada, por que a abordagem óbvia
> falha)? Se a resposta se sustenta inteira sozinha, o `<think>` é decorativo — rejeite.

Um `<think>` load-bearing contém pelo menos um destes, e a resposta visível **depende**
dele em vez de re-derivá-lo:

- **por que a abordagem ingênua não serve** (ex.: "termo a termo não vale aqui porque a
  convergência não é uniforme — preciso de convergência dominada"), decidido *antes* de
  qualquer linha de LaTeX da execução;
- **qual é a dificuldade real** antes de resolver (o que especificamente impede a solução
  trivial);
- **a escolha genuína entre duas técnicas plausíveis** — comparando as duas, não só
  anunciando a vencedora;
- **a verificação da forma** (substituir direto no ponto: é mesmo `0/0`, `∞/∞`, `0·∞`…? ou
  a "indeterminação" é falsa e resolve por continuidade?).

## O que vai no `<think>` vs. o que fica visível

O turno `assistant` é literalmente
`"<think>\n<deliberação>\n</think>\n\n<resposta visível>"`.

**Dentro do `<think>` — deliberação, estilo cru, pensando alto:**
- verificação da forma + dificuldade real + escolha de método (os "passos 1 e 2" do
  gerador antigo migram inteiros pra cá);
- frases mais curtas e diretas que a prosa técnica final; reconsiderações explícitas
  quando forem reais ("na verdade isso não separa porque…");
- **sem `<tool_call>` dentro** — a decisão de chamar a tool pode ser deliberada no think,
  mas a tag em si vem depois do `</think>`.

**Depois do `</think>` — execução limpa, mais enxuta que uma resposta sem think:**
- a álgebra/cálculo **linha a linha em LaTeX** (isto continua obrigatório — a deliberação
  ter saído pro think não dispensa mostrar a conta sendo feita);
- verificação cruzada por caminho independente;
- resposta final única em `\boxed{}` quando fizer sentido.

Como a parte "por que essa técnica" já aconteceu no think, o texto visível **não
reargumenta a escolha do zero** — ele executa. É assim que se enxerga que o think está
carregando peso: some a deliberação da parte visível, ela vira execução pura.

## Deliberação real ≠ teatro

O risco oposto ao pós-hoc é inventar dúvida onde não há. Regras:

- Problema **sem armadilha** tem think **curto** — a deliberação genuína pode ser uma frase
  ("substituição direta resolve, a função é contínua no ponto; sem indeterminação, sem
  L'Hôpital") e pronto. Não infle.
- Não force um "caminho abandonado" num problema que não tem bifurcação real. Beco-sem-saída
  só entra quando o problema genuinamente induz a um, e aí **deixe o beco no think** (foi o
  que aconteceu ao resolver de verdade) em vez de apagá-lo pra deixar limpo.
- A extensão do `<think>` segue a dificuldade real, não uma meta de palavras. Camada 3 dura
  costuma pedir 8–20 linhas de deliberação; camada 2 de rotina, 1–4.

## Fidelidade tool → resposta (regra dura, verificada por script)

Quando o item usa `python_sandbox`, `src/validate_data.py` **reexecuta o código e exige que
o número do stdout reapareça na resposta final** (motivo de rejeição
`resposta_nao_ecoa_resultado_tool`). Foi o modo de falha nº 1 do modelo — o sandbox devolveu
`6907.5` e a resposta escreveu `6.906,75`. Portanto:

- a resposta final **tem que conter o resultado do stdout**, idêntico (arredondamento
  explícito e conversão de unidade tudo bem — `6907.5` → `R$ 6.907,50` passa; `6906,75` não);
- o `<think>` que segue o resultado da tool avalia se ele bate com o esperado, e a resposta
  é função desse número — nunca contradiz o checker;
- o código tem que calcular **a quantidade do problema** (não uma expressão qualquer que
  roda) e terminar em `print()` do resultado.

Estrutura, seguindo o invariante do projeto (nunca fabricar stdout): o turno `assistant`
termina no `<tool_call>`, o objeto JSON leva `"_needs_execution": true`, e o Lucas executa
de verdade e completa o episódio (turno `tool` real + `<think>` curto de avaliação +
resposta final). O `<tool_call>` usa o formato nativo Qwen3:
`<tool_call>\n{"name": "python_sandbox", "arguments": {"code": "..."}}\n</tool_call>`.

## Regras de formato

- **Só LaTeX** para toda expressão matemática — nada de unicode solto (`∛`, `²`, `→`)
  misturado com LaTeX. Use `\sqrt[3]{}`, `\frac{}{}`, `\lim\limits`, `\displaystyle`.
- `<think>` sempre no **início** do `content`, fechado com `</think>`, seguido de `\n\n` e
  da resposta. Nunca deixar `<think>` sem `</think>`; nunca aninhar tags.
- `<tool_call>` **fora** do `<think>`, sempre. É o único marcador estrutural permitido.
- Sem markdown de chat do próprio GPT-5.6: sem "Aqui está a resolução:", sem `---`, sem
  emoji, sem headers `#`/`##` dentro do turno.
- Português técnico (pt-BR) **ou** inglês conforme o enunciado; nunca misturar no mesmo item.
- **Anti-frase-fôrma**: num lote, a abertura do `<think>` e a conectiva de verificação
  cruzada não podem repetir mais que ~3 vezes (mesmo `ngram_max_freq: 3` do validador).
  Varie de verdade a primeira frase do think entre os itens — pelo menos 10 formulações
  distintas por lote de 50. Nada de todos abrirem com "Antes de aplicar a técnica…".

## Estrutura por problema (o que pedir)

Cole o enunciado em LaTeX puro (sem paráfrase) e produza, nesta ordem lógica:

1. **`<think>`** — verificação da forma → dificuldade real → escolha de método justificada
   (comparando alternativas quando houver), *antes* de qualquer execução. Se resolveu de
   verdade e tropeçou, o tropeço fica aqui.
2. **`</think>` + execução** — álgebra linha a linha em LaTeX, cada manipulação decorrendo
   da anterior; proibido pular de "aplicando X" pro resultado.
3. **Verificação cruzada** — caminho independente do passo 2: método alternativo,
   substituição numérica, caso-limite/análise dimensional (física), ou `python_sandbox`
   quando o valor se confirma por código.
4. **Resposta final única** em `\boxed{}` quando couber — sem reabrir dúvida, sem
   contradizer a derivação nem o checker.

Se o checker (quando usado) discordar da conta manual: reconheça em uma frase qual passo
furou, recalcule, e não reabra — o checker é a palavra final, nunca entregue dois valores.

## Cobertura — generalizar o procedimento, não memorizar respostas

Vale integralmente o eixo de heterogeneidade do `generator_math_gpt56.md`: varie nível
(superior/mestrado/doutorado para camada 3), armadilha (misture forma-que-parece-
indeterminada-mas-não-é com indeterminação genuína e com problemas retos sem pegadinha) e
uso de tool. Nunca dois problemas seguidos que só trocam números da mesma forma funcional.
As famílias e o tamanho de lote (50 por família, ~4 rodadas de 12–15) seguem aquele
documento — este aqui muda **como** cada item é escrito (think-first, com `<think>`), não
**quais** problemas entram.

## Schema de saída — JSONL pronto, uma linha por problema

Sem tool (maioria — verificação cruzada algébrica/numérica no próprio texto):

```json
{"layer": "3", "lang": "pt-BR", "messages": [{"role": "user", "content": "<enunciado em LaTeX>"}, {"role": "assistant", "content": "<think>\n<deliberação>\n</think>\n\n<execução em LaTeX + verificação cruzada + \\boxed{}>"}]}
```

Com `python_sandbox` de verdade (o assistant para no `<tool_call>`; Lucas executa e completa):

```json
{"layer": "3", "lang": "pt-BR", "_needs_execution": true, "messages": [{"role": "user", "content": "<enunciado>"}, {"role": "assistant", "content": "<think>\n<deliberação até decidir chamar a tool>\n</think>\n\n<preâmbulo curto>\n<tool_call>\n{\"name\": \"python_sandbox\", \"arguments\": {\"code\": \"...print(resultado)\"}}\n</tool_call>"}]}
```

Regras de emissão:
- `layer`: `"2"` (rotina, think curto) ou `"3"` (difícil, think longo).
- `lang`: `"pt-BR"` ou `"en"` conforme o enunciado.
- **Sem markdown ao redor**: nada de crase tripla, nada de texto antes/depois. Um lote é um
  JSONL — uma linha por objeto, sem vírgula entre linhas, sem `[...]` envolvendo.
- Escapar `\` e `"` corretamente dentro das strings JSON (LaTeX vira `\\`, aspas viram `\"`).

## Checklist antes de eu aceitar

1. **Teste contrafactual**: apagando o `<think>`, a resposta visível fica sem justificativa
   para ao menos uma escolha? Se não, o think é decorativo → rejeitar.
2. **Ordem correta**: a deliberação (por que o método / dificuldade real) está no `<think>`,
   ANTES da execução — não colada depois do `\boxed{}` como justificativa retroativa.
3. Resultado matemático **correto** (resolvido do zero — se o think leva ao valor errado,
   descartar o item inteiro, não consertar).
4. Execução visível linha a linha em LaTeX (não virou resumo em prosa porque a deliberação
   saiu pro think).
5. Sem contradição entre `<think>`, execução, checker e resposta final.
6. Fidelidade tool→resposta: se há `python_sandbox`, a resposta contém o resultado do stdout
   (o validador reprova `resposta_nao_ecoa_resultado_tool`); o código calcula a quantidade
   do problema e termina em `print()`.
7. `<think>` bem-formado (início do turno, fechado, sem `<tool_call>` dentro), LaTeX sem
   unicode solto, `_needs_execution` marcado quando há tool.
8. Sem abertura de `<think>` nem conectiva de verificação repetida verbatim no lote.
9. Extensão proporcional à dificuldade real — think curto em problema reto, longo só no que
   é genuinamente difícil.
