# Brief para o GPT-5.6 (raciocínio xhigh) — distilação de matemática/física

Este arquivo é para ser colado como instrução (system ou primeira mensagem) numa conversa
com o GPT-5.6 em modo de raciocínio estendido. O objetivo: gerar respostas-professor de
altíssima qualidade para problemas de matemática/física que depois viram exemplos de
treino (camadas 2 e 3, ver `prompts/generator_system.md` e `configs/gen_config.yaml`) do
Conatus Phronesis — um modelo pequeno que hoje comete erros de rigor nessa área.

O GPT-5.6 escreve DIRETO no formato final do dataset — um objeto JSON por problema, já no
schema `messages` (ver seção "Formato de saída exigido" abaixo). Ninguém reformata depois;
ele produz o JSONL pronto, problema por problema, na ordem das famílias já listadas neste
documento.

## Como funciona o template do modelo-alvo (importante ler antes de gerar)

O Phronesis é um Qwen3 fine-tunado. O `content` do turno `assistant` que o GPT-5.6 escreve
vai, sem edição, virar literalmente o texto entre `<|im_start|>assistant` e `<|im_end|>` no
chat template — então tem que respeitar as regras nativas desse formato, não o estilo de
resposta do próprio GPT-5.6 (que costuma separar "reasoning" de "resposta final" em canais
distintos na sua própria interface):

- **Proibido bloco `<think>...</think>`**: o raciocínio não fica escondido em canal
  separado — é texto comum, visível, ANTES da resposta final (ou antes do `<tool_call>`,
  quando houver). Se o GPT-5.6 normalmente produz reasoning oculto e só expõe a resposta,
  aqui isso é errado: cole o raciocínio completo, em prosa técnica + LaTeX, como o próprio
  corpo da mensagem.
- **`<tool_call>` é o único marcador estrutural permitido**, e só na exceção de código
  real (ver abaixo) — formato exato:
  `<tool_call>\n{"name": "python_sandbox", "arguments": {"code": "..."}}\n</tool_call>`,
  com o raciocínio em texto comum imediatamente antes (nunca depois, nunca dentro da tag).
- **Schema da tool** (`configs/tools.json`): `python_sandbox` recebe só `{"code": string}`
  — o código precisa terminar com `print()` do resultado, porque é o stdout que vira o
  turno `tool` real depois.
- Fora isso, o `content` é texto/LaTeX puro — sem markdown de chat próprio do GPT-5.6
  (sem "Aqui está minha resolução:" de abertura performática, sem separador tipo `---`
  entre "raciocínio" e "resposta", sem emoji, sem headers `#`/`##` dentro do turno).

## O erro concreto que estamos corrigindo

Transcrição real do Phronesis (produção, 2026-07-22) para
`lim_{x→27} (∛x − 1)/(x − 2)`:

> "O limite é indeterminado na forma 0/0 [...] resposta é 1/9 [...]"
> depois deriva por substituição direta `(∛27 − 1)/(27 − 2) = 2/25`
> depois diz "o erro está na passagem de limites [...] resposta correta é 1/9"

Dois defeitos empilhados:
1. **Alucinação de indeterminação**: em `x=27` o denominador vale `25` e o numerador
   vale `2` — não há 0/0 nenhum, é substituição direta numa função contínua no ponto.
   O modelo inventou uma indeterminação que não existe e partiu pra racionalização
   desnecessária.
2. **Autocontradição não resolvida**: o texto final desautoriza a própria conta correta
   (2/25, que ele mesmo calculou certo) e reafirma um número (1/9) que não aparece em
   nenhuma derivação do texto. Isso é pior que estar errado — é incoerência interna que
   o modelo não detecta sozinho.

O objetivo da distilação é ensinar o padrão que evita as duas coisas: **verificar a forma
antes de escolher a técnica**, e **nunca fechar a resposta em contradição com a própria
derivação**.

## Segundo bug real: o modelo pula a resolução

Hoje, em produção, o Phronesis frequentemente dá só uma explicação breve seguida do
resultado — sem mostrar a conta sendo resolvida passo a passo em LaTeX. Isso é tão
problemático quanto o bug de indeterminação falsa: um usuário que pede "calcule X" quer
ver a derivação, não só a explicação de qual técnica se aplicaria e o valor final. Toda
resposta distilada do GPT-5.6 **precisa mostrar o desenvolvimento algébrico completo em
LaTeX, linha a linha**, do jeito que um professor resolveria no quadro — nunca resumir a
conta em prosa e só entregar o resultado. Isso vale mesmo pra camada 2 (compacta, mas
ainda assim com as linhas de álgebra visíveis, não uma frase dizendo "resolvendo, dá X").

## Terceiro bug real: verificação fabricada/desconectada + surdez a instrução de formato

Transcrição real do Phronesis (produção): pedido "calcule \(\lim_{x\to0}3x^2/x\)" seguido,
na mensagem seguinte, de "que mostre o passo a passo da resolução". O modelo devolveu, nas
DUAS vezes, a frase idêntica ("o limite é indeterminado, mas a função simplifica para 3x
que tende a zero") e o MESMO tool call:

```
{"name": "python_sandbox", "arguments": {"code": "print(f'{(0.1)*23/0.1:.6f}')"}}
```

Dois defeitos novos, além do já documentado (pular a resolução):

1. **Surdez a instrução explícita de formato**: pedir "mostre o passo a passo" na segunda
   mensagem não mudou nada na resposta — o modelo repetiu a mesma frase word-by-word.
   Instrução de formato do usuário tem que alterar a resposta; se não altera, é sinal de
   que o modelo nunca viu exemplo de treino onde um pedido de "step by step" resulta em
   desenvolvimento visivelmente mais longo/detalhado que a resposta anterior.
2. **Verificação fabricada, sem relação com o problema**: o código `(0.1)*23/0.1` calcula
   `23.0` — não tem nada a ver com `3x²/x`. O código correto seria algo como
   `print(3*(0.001)**2/0.001)` → `0.003`, coerente com o limite `0`. Rodamos os dois pra
   confirmar. Isso é pior que pular a verificação: é produzir uma verificação que parece
   real (roda, imprime um número) mas não testa a quantidade certa — o tipo de erro que
   um leitor apressado não pega porque "tem código e tem número".

**Implicação pro checklist de aceitação**: item 6 do checklist ("se há código, ele executa
e o stdout bate com o valor afirmado") não é suficiente sozinho — precisa também conferir
que o código de fato calcula a quantidade do problema (não uma expressão qualquer que por
acaso roda sem erro). Ao revisar cada resposta do GPT-5.6, reler o código e confirmar que
as variáveis/expressões correspondem literalmente ao enunciado antes de rodar.

## Quarto bug real: frase-fôrma nas 50 respostas do primeiro lote

Rodamos `src/validate_data.py` no primeiro lote completo de 50 (família "limites") e as
50 passaram — 0 rejeitados. Isso não quer dizer que estava tudo certo: o filtro de
repetição de n-grama do validador (`rationale_layers = {"0.5", "1"}` em
`validate_data.py`) só roda pras camadas 0.5 e 1, porque até agora ninguém tinha gerado
camada 2/3 em lote — sempre foi escrito um a um à mão. É um ponto cego real do validador,
não prova de qualidade.

Inspecionando à mão: **as 50 respostas começam, literalmente, com a mesma frase
"Verificação da forma:"** — 50 de 50, verbatim — e 44 das 50 usam a mesma transição "Como
verificação cruzada," / "Como verificação independente,". Isso é o mesmíssimo padrão de
frase-fôrma que `generator_system.md` já proíbe pra camada 1 ("Proibido repetir
frase-fôrma... no mínimo 8 formulações distintas"). O conteúdo matemático de cada resposta
é correto e específico ao problema — o defeito é puramente na casca retórica, repetida
sem variação.

**Regra nova, obrigatória a partir daqui**: nenhuma abertura de "verificação da forma" ou
transição de "verificação cruzada" pode se repetir mais que ~3 vezes num lote de 50 (mesmo
limite `ngram_max_freq: 3` já usado em `configs/gen_config.yaml`). Peça ao GPT-5.6
explicitamente pra variar a abertura de cada resposta (ex.: "O numerador e o denominador
se anulam simultaneamente, então..." / "Antes de aplicar [técnica], convém checar se..." /
"Substituindo diretamente..." / "O comportamento em [ponto] decide a forma:..." — pelo
menos 10+ formulações distintas por lote de 50) e a conectiva de verificação cruzada
(ex.: "Confirmando por outro caminho:" / "Um teste independente:" / "Pra não confiar só
nessa conta:" / "Cruzando com [método alternativo]:"). Isso vale igualmente pro lote de
"limites" já gerado — pedir ao GPT-5.6 uma reescrita das aberturas/transições antes de
aceitar como está, mantendo a matemática igual.

## Quinto ponto: profundidade real do raciocínio, não só a prova final polida

Medimos o lote de 50: camada 2 tem média de 68 palavras por resposta (ok, é pra ser
compacta); mas **camada 3 — os problemas genuinamente difíceis (prova de reordenação em
espaço de Banach, convergência \(L^p\to L^\infty\), Fourier) — tem média de só 130
palavras, máximo 196**. Isso é curto demais pro que a camada 3 pede ("raciocínio longo
justificado, 15–30 linhas"): o que veio foi a demonstração já pronta e polida, no estilo
de livro-texto — aplica a técnica certa direto, sem nunca mostrar por que uma abordagem
mais óbvia falharia ou por que essa é a escolhida entre alternativas. É a resposta do
quadro-negro, não o rastro de deliberação que presumivelmente aconteceu no raciocínio
"oculto" do GPT-5.6 antes de chegar lá — e é justamente esse rastro de deliberação
visível que queremos destilar, não só a prova final correta (que já sabíamos que ele
consegue produzir).

**Instrução adicional pra camada 3 — a deliberação é parte dos passos 1–2, não um adendo
depois da resposta.** Os passos já definidos na seção "O que pedir ao GPT-5.6, por
problema" são, nessa ordem: (1) verificação da forma, (2) escolha do método, (3) execução
limpa, (4) verificação cruzada, (5) resposta final. O aprofundamento entra DENTRO dos
passos 1 e 2 — que hoje saem como uma frase cada — nunca como um parágrafo extra colado
depois do passo 5. Se o texto resolver primeiro e só depois explicar por que outra
abordagem seria pior, está na ordem errada: o motivo de descartar a abordagem ingênua
tem que aparecer ANTES de qualquer linha de LaTeX da execução, porque é isso que justifica
a escolha do método — explicar depois de já ter resolvido não é deliberação, é
justificativa retroativa.

Ao expandir os passos 1–2, exigir que o texto mostre pelo menos um destes, quando genuíno
ao problema (não forçar se não houver):
- por que uma abordagem mais direta/ingênua não se aplica ou seria pior (ex.: "tentar
  limite termo a termo aqui não é válido porque..." antes de escolher convergência
  dominada);
- qual é a dificuldade real do problema antes de resolvê-la (o que especificamente
  impede a solução trivial);
- ao escolher entre duas técnicas plausíveis, uma frase comparando as duas, não só
  anunciando a escolhida.

Isso deve levar camada 3 pra mais perto de 200–350 palavras nos casos genuinamente
difíceis (não é meta rígida — a extensão segue a dificuldade real, não um mínimo
artificial de palavras). Ao revisar a reescrita, checar a ORDEM antes de checar o
conteúdo: se a frase de deliberação aparece depois do `\boxed{}` ou depois da última linha
de álgebra, rejeitar e pedir de novo, mesmo que o conteúdo da frase esteja correto.

## Cobertura de problemas — generalizar o procedimento, não memorizar respostas

O objetivo não é um exemplo bonito de limite — é destilar o **procedimento** (verificar
forma → escolher método → executar → checar cruzado → corrigir se preciso → responder)
de um jeito que generalize pra problema nunca visto. Isso só acontece se o lote for
deliberadamente heterogêneo. Um lote de 30 limites parecidos ensina "como fazer limite",
não "como verificar antes de agir" — que é a lição real.

Ao montar o lote de problemas pra mandar ao GPT-5.6, varie nos três eixos:

- **Nível: superior/mestrado/doutorado.** Nada de ensino médio ou cálculo 1 introdutório
  isolado — os problemas devem exigir ferramental de graduação avançada ou pós. Isso
  muda o que entra em cada família abaixo: limites e séries viram análise real (ε-δ
  formal, convergência uniforme, séries de Fourier, teste de convergência menos óbvio
  que razão/raiz); derivadas/integrais viram cálculo vetorial e análise complexa
  (integrais de contorno, resíduos, teoremas de Green/Stokes); EDOs viram EDPs
  (separação de variáveis, transformada de Laplace/Fourier aplicada); álgebra linear
  vira formas quadráticas, decomposição espectral, espaços vetoriais abstratos; inclua
  também topologia básica, álgebra abstrata (grupos/anéis), teoria da medida quando
  fizer sentido. Física: mecânica quântica introdutória (poço de potencial, oscilador
  harmônico), mecânica estatística, eletrodinâmica (equações de Maxwell, ondas),
  mecânica lagrangiana/hamiltoniana, relatividade restrita — não física do ensino médio.
- **Armadilha (ou ausência dela)**: inclua deliberadamente casos como o do bug (forma que
  *parece* indeterminada mas não é — substituição direta resolve) misturados com casos de
  indeterminação genuína real, e com problemas sem armadilha nenhuma (retos). Se todo
  problema do lote for "pegadinha", o modelo aprende a desconfiar de tudo; se nenhum for,
  não aprende a desconfiar quando deveria. A mistura é a lição.
- **Dificuldade e uso de tool**: alguns só de raciocínio algébrico (sem sandbox), alguns
  que pedem verificação numérica de rotina (camada 2), alguns genuinamente difíceis com
  raciocínio longo (camada 3, com ou sem sandbox) — não force sandbox em problema que se
  verifica por álgebra pura, e não force raciocínio longo em conta simples.

Regra prática: nunca mande dois problemas seguidos que só trocam os números da mesma
forma funcional. Se dois problemas do lote resolvem com exatamente os mesmos passos na
mesma ordem, um dos dois está sobrando — troque de família ou de armadilha antes de gerar
o próximo.

## Tamanho do lote — 50 por família

Em vez de misturar tudo num pool único, organize por família fechada, **50 problemas por
família**. Famílias iniciais (todas nível superior/mestrado/doutorado, ver eixo acima):

1. Limites e séries (análise real: ε-δ, convergência uniforme, Fourier)
2. Álgebra linear (formas quadráticas, decomposição espectral, espaços abstratos)
3. Física matemática / fismat (lagrangiana/hamiltoniana, EDPs da física, eletrodinâmica,
   mecânica quântica introdutória)
4. Análise complexa (integrais de contorno, resíduos, séries de Laurent)
5. Equações diferenciais (EDOs de ordem superior, EDPs, transformadas de Laplace/Fourier)
6. Física 1 (mecânica clássica: cinemática, dinâmica, trabalho/energia, momento linear e
   angular, rotação de corpo rígido)
7. Física 2 (termodinâmica, oscilações, ondas mecânicas, fluidos)
8. Física computacional (métodos numéricos aplicados a física: integração numérica,
   solução numérica de EDOs — Euler, Runge-Kutta —, Monte Carlo, diferenças finitas,
   análise de erro/convergência do método)

**Física 3 (eletromagnetismo) e Física 4 (física moderna/quântica) foram removidas desta
lista**: ao mapear os 50 itens já gerados de "física matemática", 11 já são eletrodinâmica
avançada (Green de Helmholtz, Maxwell, Poynting, calibre, multipolos, imagens,
reciprocidade, potenciais retardados) e 19 já são mecânica quântica completa (poço
infinito, operadores escada, espalhamento, incerteza, spin, Ehrenfest, momento angular,
perturbação degenerada, variacional, WKB, propagador, Aharonov-Bohm) — 30 dos 50 itens
daquela família já cobrem o que física 3/4 fariam, em nível avançado. Gerar essas duas
famílias de novo seria majoritariamente redundante.

Dentro de cada bloco de 50 continuam valendo os eixos de armadilha e dificuldade já
descritos: ~20 camada 2, ~20 camada 3, ~10 "armadilha tipo bug" espalhadas (não em bloco
separado). Cada família é resolvida e revisada como unidade fechada antes de passar pra
próxima — mais fácil de garantir que os 50 problemas daquela família não repetem a mesma
forma funcional com números trocados (ver regra prática acima).

**Exceção da física computacional**: por natureza, quase todo problema dessa família usa
`python_sandbox` de verdade (é o ponto da família — implementar e rodar o método
numérico), então a distribuição ~20/~20/~10 não se aplica igual; o que continua valendo é
a verificação cruzada (comparar contra solução analítica quando existir, ou refinar o
passo/malha e checar convergência) e o passo a passo mostrado antes do código — o
raciocínio de por que aquele método/passo, não só o código pronto.

Por rodada de chat com o GPT-5.6: 12–15 problemas (de uma mesma família por vez), então
cada família de 50 leva ~4 rodadas.

## O que pedir ao GPT-5.6, por problema

Cole o enunciado (LaTeX puro, sem paráfrase) e peça exatamente esta estrutura:

1. **Verificação da forma** — antes de aplicar qualquer técnica (L'Hôpital,
   racionalização, expansão em série, regra de Leibniz etc.), avalie a expressão
   diretamente no ponto/limite. Só prossiga com uma técnica se a forma for de fato
   indeterminada (`0/0`, `∞/∞`, `0·∞`, `∞−∞`, `0^0`, `1^∞`, `∞^0`). Se não for, diga
   isso explicitamente e resolva por substituição/continuidade.
2. **Escolha do método justificada em 1 frase** — por que essa técnica e não outra.
3. **Execução limpa em LaTeX, passo a passo, sempre** — cada manipulação algébrica
   aparece como uma linha de equação, não como frase resumindo o que foi feito. Proibido
   pular direto de "aplicando [técnica]" pro resultado — se são 5 manipulações, são 5
   linhas de LaTeX visíveis, cada uma decorrendo da anterior. Notação padrão
   (`\displaystyle`, `\lim\limits`, `\sqrt[n]{}`, frações como `\frac{}{}`, nunca unicode
   tipo `∛` ou `²` misturado com LaTeX).
4. **Verificação cruzada obrigatória** — confirme o resultado por um caminho
   independente do usado no passo 3: substituição numérica próxima do ponto, um método
   alternativo (ex.: L'Hôpital vs. racionalização), ou checagem de caso-limite/dimensão
   (física). Use o `python_sandbox` (sympy/numpy) como esse caminho independente sempre
   que der — é o mesmo checker que o Phronesis já usa em produção, então a distilação
   fica no formato que o modelo pequeno realmente vai reproduzir.
5. **Se o checker discordar da derivação manual**: o GPT-5.6 se corrige explicitamente e
   segue em frente — reconhece o erro em 1 frase (qual passo furou), recalcula, e não
   reabre o caso depois. Mesmo padrão de `self_correction` da camada 2 em
   `generator_system.md`: sem autoflagelação, sem hedging repetido, sem imprimir dois
   valores concorrentes. O checker é a palavra final; nunca entregar dois valores
   diferentes na mesma resposta.
6. **Resposta final única** — uma frase, um valor, em `\boxed{}` quando fizer sentido.
   Proibido reabrir dúvida ou contradizer a derivação (ou o resultado do checker) depois
   do resultado final.

## Regras de formato

- Só LaTeX para toda expressão matemática (nada de unicode substituindo símbolo).
- CoT tecnicamente denso: sem enrolação, sem "vamos pensar juntos" — direto ao raciocínio,
  frase por frase carregando informação nova.
- Extensão: 15–30 linhas de raciocínio para problema genuinamente difícil (camada 3);
  3–6 linhas + verificação numérica para cálculo de rotina (camada 2) — decida pela
  dificuldade real do problema, não infle.
- Se o problema pede um valor que dá pra confirmar por código (sympy/numpy), inclua ao
  final um bloco de código Python autocontido e correto que imprime o resultado — esse
  código eu executo de verdade (nunca fabricamos stdout; ver invariante em
  `eidos/data/build_episodes.py` e `src/inference_loop.py`), então ele precisa rodar sem
  editar nada.
- Português técnico (pt-BR) ou inglês conforme o problema-fonte; nunca misturar no meio
  da mesma resposta.

## Checklist antes de eu aceitar a resposta no dataset

1. O passo 1 evita indeterminação falsa? (testar: dá pra substituir direto?)
2. A verificação cruzada do passo 4 existe e bate com o resultado do passo 3? Se não
   bateu no rascunho, a correção do passo 5 aconteceu de forma explícita e única (sem
   ping-pong de valores)?
3. Zero contradição entre qualquer parte do texto e a resposta final.
4. LaTeX consistente, sem unicode matemático solto.
5. **A resolução aparece de verdade, linha a linha** — se o texto só explica em prosa e
   dá o resultado sem mostrar a álgebra/cálculo sendo feito, rejeitar e pedir de novo.
6. Se há código, ele executa e o stdout bate com o valor afirmado no texto.
7. Extensão proporcional à dificuldade real (não é camada 3 só porque é longo).

## Formato de saída exigido — JSONL pronto, sem intermediário

Cada problema vira UMA linha JSON, nesse schema exato (mesmo de `generator_system.md`):

```json
{"layer": "2", "lang": "pt-BR", "messages": [{"role": "user", "content": "<enunciado em LaTeX>"}, {"role": "assistant", "content": "<CoT passo a passo em LaTeX + verificação cruzada + resposta final>"}]}
```

Regras de emissão:

- `layer`: `"2"` (cálculo/verificação de rotina) ou `"3"` (genuinamente difícil, raciocínio
  longo) — conforme decidido no eixo de dificuldade.
- `lang`: `"pt-BR"` ou `"en"`, conforme o idioma do enunciado.
- `messages` tem exatamente 2 turnos (`user`, `assistant`) quando a verificação cruzada é
  só algébrica/numérica feita no próprio texto (sem tool real) — que é o caso da imensa
  maioria dos problemas.
- **Sem markdown ao redor**: nada de crase tripla, nada de texto antes/depois do JSON.
  Uma linha = um objeto JSON válido. Ao entregar um lote de 12–15 problemas, é um JSONL
  (uma linha por problema, sem vírgula entre linhas, sem colchete `[...]` envolvendo tudo).
- Ordem: sempre a ordem das famílias listadas em "Tamanho do lote", uma família de cada
  vez, do primeiro ao quinquagésimo problema daquela família antes de passar pra próxima.

### Exceção — problemas que usam `python_sandbox` de verdade (típico da física computacional)

Nesses casos o GPT-5.6 NÃO fabrica o turno `tool` (nunca inventamos stdout — é invariante
do projeto, ver `eidos/data/build_episodes.py`). Em vez disso:

- O turno `assistant` termina no `<tool_call>` (formato nativo Qwen3:
  `<tool_call>\n{"name": "python_sandbox", "arguments": {"code": "..."}}\n</tool_call>`,
  precedido do raciocínio/preâmbulo em texto comum).
- `messages` tem só esses 2 turnos (`user`, `assistant` terminando em `<tool_call>`) —
  SEM turno `tool` e SEM segundo turno `assistant`. Eu executo o código de verdade e
  completo o episódio (turno `tool` real + resposta final) antes de aceitar.
- Adicione o campo `"_needs_execution": true` no objeto JSON pra eu saber que esse item
  ainda precisa da execução real antes de entrar em `data/clean/`.

## Onde isso vira dataset de verdade

Você recebe o JSONL do GPT-5.6 (um bloco por rodada de 12–15 problemas) e me passa aqui.
Eu:

1. Confiro cada linha contra o checklist acima (rejeito e devolvo pra refazer se falhar).
2. Salvo as aprovadas em `data/raw/gpt56_<família>.jsonl` (ex.:
   `data/raw/gpt56_limites.jsonl`, `data/raw/gpt56_fisica1.jsonl`) — um arquivo por
   família de 50, mesma convenção de `data/raw/pilot.jsonl`.
3. Para as marcadas `_needs_execution`: rodo o código real, completo o turno `tool` e a
   resposta final, removo a marca, e só então elas entram no arquivo da família.
4. Ao fechar os 50 de uma família, rodo `python src/validate_data.py
   data/raw/gpt56_<família>.jsonl`, que gera/atualiza `data/clean/dataset.jsonl`
   (aprovados), `data/clean/rejected.jsonl` (com motivo) e `data/clean/report.json`.
5. `data/clean/dataset.jsonl` alimenta depois `src/build_dataset.py` pra virar
   `train.jsonl` com máscara de loss.

O único trabalho manual que sobra pra mim é validar, rodar código real quando marcado, e
salvar no arquivo certo — nenhuma reformatação de prosa em JSON.

## Sexta família (fora do padrão): Cálculo 1/2/3 rápido, com autocorreção real

As três famílias anteriores (limites, álgebra linear, física matemática) são todas
difíceis e longas de propósito. Se o dataset inteiro for assim, o modelo aprende que toda
pergunta de matemática merece 150-250 palavras de deliberação — o que é tão errado quanto
o bug original de pular a resolução. Esta família existe pra ensinar o oposto: calibrar o
esforço pela dificuldade real, e treinar autocorreção genuína (que nenhuma das 150
respostas anteriores exercitou, porque o GPT-5.6 sempre acertou de primeira).

**Esta família SOBRESCREVE duas regras gerais deste documento, só pra ela:**
- **Nível**: NÃO é superior/mestrado/doutorado. É Cálculo 1/2/3 de graduação —
  exatamente o nível dos dois bugs reais de produção que abriram este projeto (`∛x`,
  `3x²/x`, ambos Cálculo 1). Nada de análise real, topologia, prova geral.
- **Extensão**: NÃO mirar 200-350 palavras. Meta: **30-80 palavras pros itens corretos de
  primeira**, **60-150 palavras pros itens com autocorreção** (o extra é o primeiro
  tentativa + a correção, não deliberação nova). Se a resposta parece um parágrafo de
  prova, está errado pra esta família — é pra parecer alguém resolvendo rápido no papel.

**50 problemas, divididos em três blocos, não 50 de cada:**
- ~18 de Cálculo 1 (limites diretos, derivadas por regras padrão — produto, quociente,
  cadeia —, otimização simples, esboço básico via primeira/segunda derivada)
- ~16 de Cálculo 2 (técnicas de integração — substituição, partes, frações parciais —,
  integrais impróprias simples, séries — teste de razão/comparação básico —, coordenadas
  polares introdutórias)
- ~16 de Cálculo 3 (derivadas parciais, gradiente, integrais duplas/triplas em regiões
  simples, divergente/rotacional, multiplicadores de Lagrange básico)

**Sem pegadinha.** Ao contrário das famílias anteriores, aqui NÃO misturar "forma que
parece indeterminada mas não é" nem armadilhas conceituais — o objetivo agora é o caminho
mais direto e correto pra cada problema, com a técnica certa escolhida sem drama. Uma
frase de escolha de método ainda cabe (ex.: "substituição direta resolve, sem precisar de
L'Hôpital"), mas curta — não é pra reintroduzir a deliberação longa das famílias
anteriores.

**Autocorreção: ~30% do lote (≈15 dos 50), mesma proporção de
`layer2_selfcorrection: 0.30` já usada em `configs/gen_config.yaml`.** Regras pra esses
itens:
- O primeiro passo do assistant é uma resolução por conta de cabeça/mental, com um erro
  **plausível e específico** — não caricato. Bons candidatos: sinal trocado numa derivada
  ou integral, esquecer a regra da cadeia num termo, trocar um limite de integração,
  aplicar a fórmula errada de uma tabela parecida, erro aritmético numa substituição.
  Ruim: erro absurdo que ninguém cometeria, ou erro conceitual grave incompatível com
  quem já sabe montar o problema certo até ali.
- Em seguida, o assistant chama `python_sandbox` pra conferir — código real, que eu vou
  executar de verdade (mesmo invariante de sempre: marcar `_needs_execution` e parar no
  `</tool_call>`).
- Quando o resultado do checker diverge do valor calculado de cabeça, a resposta final
  reconhece em UMA frase, sem drama nem autoflagelação, e dá o valor certo — o padrão
  exato já descrito em `generator_system.md` pra camada 2: "Ops, [erro específico] — o
  valor certo é [X]." ou variações (não repetir a mesma fórmula de frase nos 15 itens;
  mesma regra de variedade das famílias anteriores).
- Nos outros ~35 itens (sem autocorreção), o assistant pode ou não usar `python_sandbox`
  pra conferir — usar quando o cálculo for propenso a erro (conta feia, muitos passos),
  pular quando for direto o bastante pra não precisar.

Tudo o mais do documento continua valendo: schema JSONL exato, sem `<think>`, LaTeX
consistente, passo a passo real (mesmo curto, mostra a conta, não só o resultado), zero
repetição de abertura entre os 50, execução real de qualquer tool call.

## Sétima família: multi-turno, o assistant precisa reagir de verdade ao follow-up

Os dois bugs reais de produção que abriram este projeto (`∛x`, `3x²/x`) eram os dois
multi-turno: o usuário pede o cálculo, o modelo responde mal, o usuário pede "mostre o
passo a passo", e o modelo **repete a mesma resposta ruim, ignorando o pedido**. Nenhum
dos 150 exemplos gerados até aqui é multi-turno — todos são um `user` e um `assistant`.
Essa família ensina especificamente a reagir de verdade ao segundo turno, não repetir o
primeiro.

**15-20 itens, cada um com pelo menos 4 mensagens** (`user`, `assistant`, `user`,
`assistant` — alguns podem ter um terceiro par se fizer sentido, seguindo o teto de 2-4
turnos de usuário já usado em `generator_system.md`). Nível: pode ser Cálculo 1/2/3 (mesma
faixa da sexta família) ou um problema das famílias anteriores — o que importa aqui é a
dinâmica dos turnos, não a dificuldade.

**Distribuir o segundo turno do usuário entre estes quatro tipos**, aproximadamente em
partes iguais:
1. **Pede mais detalhe** ("mostra o passo a passo", "explica melhor essa parte", "não
   entendi como chegou nisso") — o primeiro `assistant` respondeu correto mas enxuto; o
   segundo precisa genuinamente expandir a derivação (mais linhas de LaTeX, não a mesma
   frase reescrita).
2. **Contesta/desconfia** ("tem certeza?", "isso não bate com o que eu calculei", "não
   parece certo") — o segundo turno reafirma com uma verificação adicional (não hostil,
   não repetitiva) OU, se o primeiro turno estava genuinamente errado, se corrige aqui
   (mesmo padrão "sem drama" da autocorreção da sexta família).
3. **Pede outra abordagem** ("dá pra resolver de outro jeito?", "e se eu usar [outra
   técnica]?") — o segundo turno resolve de fato por um caminho diferente do primeiro, e
   confirma que os resultados batem.
4. **Pergunta "por que não X"** ("por que não [técnica plausível mas pior/inaplicável]?")
   — o segundo turno explica concretamente por que essa técnica seria pior ou não se
   aplica, sem inventar uma razão genérica.

**Regra dura, verificável mecanicamente**: o texto do segundo `assistant` não pode
repetir nenhuma frase completa do primeiro `assistant` na mesma conversa (nem
parafraseada de forma óbvia). Vou checar isso comparando os dois turnos de cada item antes
de aceitar — se a segunda resposta for a primeira colada de novo (como no bug real do
`3x²/x`), rejeito o item.

Uma fração pequena (uns 3-4 dos 15-20) pode ter o primeiro turno **genuinamente incompleto
ou impreciso** (não errado no valor final, só raso) — esses ilustram melhor o padrão "pedi
mais detalhe e ele realmente elaborou", que é o caso mais comum na prática.

## Injeção nas famílias futuras: sandbox com código quebrado, o modelo debuga

Todo `python_sandbox` gerado até agora rodou certo de primeira. Isso não ensina o que
fazer quando o próprio código do modelo tem um bug — uma habilidade diferente da
autocorreção matemática da sexta família (lá o erro é na conta mental; aqui o erro é no
código, e a matemática por trás pode estar certa).

Isso não é uma família própria — é uma variação a injetar nas famílias com tool que ainda
vamos gerar (física 1-4, computacional, equações diferenciais, análise complexa): cerca de
**10 itens no total, espalhados entre elas**, não concentrados numa família só.

**Como funciona, estruturalmente:**
- O primeiro `<tool_call>` do assistant tem um bug real de código — não um erro
  matemático disfarçado de erro de código. Bons candidatos: nome de variável não
  definida, import faltando, índice fora do range, parêntese não fechado, usar `sp.Symbol`
  sem importar `sympy`, dividir por um símbolo que sympy não consegue simplificar sem
  assumption. O bug tem que ser o tipo de coisa que um programador comete rápido, não um
  erro absurdo.
- Eu executo esse código quebrado de verdade e uso o traceback/erro REAL como turno
  `tool` — mesmo invariante de sempre, agora também vale pro caso de erro: nunca fabricar
  a mensagem de erro, ela tem que ser o que o Python realmente devolve.
- O assistant seguinte lê o erro, identifica a causa específica (não um "vou tentar de
  novo" genérico) e emite um segundo `<tool_call>` corrigido.
- Esse item precisa de **dois ciclos de execução real**, então o objeto JSON leva
  `"_needs_execution": true` do mesmo jeito, e eu vou completá-lo em duas rodadas: primeiro
  rodo o código quebrado (pra pegar o erro real), depois o corrigido (pra pegar o
  resultado real), e só então fecho o episódio com a resposta final.
- Estrutura final esperada, depois que eu completo: `user`, `assistant` (código com bug),
  `tool` (erro real), `assistant` (código corrigido, com uma frase reconhecendo o que
  causou o erro), `tool` (resultado real), `assistant` (resposta final) — 6 mensagens.

Ao gerar as próximas famílias, marcar ~1 em cada 5-6 itens que já teriam tool call pra
seguir esse padrão em vez do fluxo direto de sucesso na primeira tentativa.
