# Adendo ao brief de lacunas — lote de rebalanceamento de camadas

Complemento de `prompts/generator_lacunas_gpt56.md`, a ser gerado **antes do próximo treino**.
Pressupõe `prompts/generator_system.md` (tabela de camadas, tetos de `<think>`, regras de
rationale) e o invariante de stdout real de `src/validate_data.py`.

Este lote não corrige comportamento — corrige **proporção**. Ele existe porque o lote anterior
(famílias A–G, 170 exemplos) desequilibrou o corpus, e a causa foi um erro de dimensionamento no
próprio brief que o gerou, não na execução.

---

## O que aconteceu

O brief de lacunas alocou **120 dos 170 exemplos às camadas 2 e 3** (famílias A, B, C, D, E) e
apenas 30 ao rebalanceamento (família G). O efeito no corpus:

| Camada | Antes (901) | Depois (1071) | Alvo |
|---|---|---|---|
| 0 | 0,115 | 0,121 | 0,20 |
| 0.5 | 0,105 | 0,092 | 0,12 |
| 1 | 0,320 | 0,269 | 0,25 |
| 2 | 0,245 | **0,317** | 0,18 |
| 3 | 0,062 | 0,061 | 0,05 |
| C | 0,152 | **0,139** | 0,20 |

A camada C **recebeu 12 exemplos e mesmo assim caiu de share**, porque o denominador cresceu 170.
A camada 2 quase dobrou a distância do alvo.

**Por que isso é urgente e não cosmético**: `data/raw/GEN_PROGRESS.md` registra que no `batch_014`
a camada C em **0,143** produziu regressão medida de coerência conversacional, corrigida ao subir
para 0,182. O corpus está hoje em **0,139 — abaixo daquele piso histórico**. Treinar agora
reintroduz um defeito que já foi diagnosticado e resolvido uma vez.

---

## Quanto gerar

Fechar todos os alvos exatamente exigiria ~249 exemplos só de camadas 0 e C, e ainda assim a
camada 2 pararia em 0,258 e a 0.5 cairia para 0,075 — porque a distorção real é o **excesso** da
camada 2 (340 de 1071), que não se corrige adicionando aos outros lados sem inflar o corpus em
mais de 50%.

Este lote busca o alvo pragmático: **tirar a camada C da zona de regressão com folga e recuperar a
camada 0**, aceitando que a camada 2 continue acima do alvo até que uma futura poda ou uma revisão
dos próprios alvos aconteça.

| Grupo | Camada | n |
|---|---|---|
| H | 0 | 60 |
| I | C | 50 |
| J | 0.5 | 25 |
| | **Total** | **135** |

Projeção com o lote aplicado (1206 exemplos):

| Camada | Antes | Depois | Alvo |
|---|---|---|---|
| 0 | 0,121 | **0,158** | 0,20 |
| 0.5 | 0,092 | **0,103** | 0,12 |
| 1 | 0,269 | 0,239 | 0,25 |
| 2 | 0,317 | 0,282 | 0,18 |
| 3 | 0,061 | 0,054 | 0,05 |
| C | 0,139 | **0,165** | 0,20 |

Camada C sai de 0,139 para 0,165 — acima do piso de 0,143 e próxima do 0,182 que funcionou. Não
chega ao alvo de 0,20, e isso é deliberado: um lote de 249 para fechar exatamente inflaria o corpus
num único eixo e diluiria as famílias A–E que acabaram de ser criadas para corrigir defeitos reais.

---

## Grupo H — camada 0 (60 exemplos)

Fato estável, definição, pergunta factual simples. **Resposta seca**, preâmbulo de **zero palavras**,
sem nenhuma tool call, `<think>` de no máximo 15 palavras.

O validador é estrito aqui e rejeita por `camada0_com_preambulo` qualquer resposta que contenha
marcadores como "vou buscar", "deixa eu", "não preciso de", "sem precisar de busca". A resposta
começa direto no conteúdo.

Distribua por domínio, 12 de cada:
- **Ciência estável**: unidades do SI, constantes, classificações biológicas, tabela periódica,
  fenômenos físicos com explicação consolidada.
- **Geografia e história consolidadas**: capitais, rios, cordilheiras, datas de eventos encerrados,
  ordem cronológica de períodos.
- **Definições técnicas**: termos de computação, matemática, linguística, economia — o que é
  recursão, o que é um número primo, o que é inflação.
- **Cultura e artes**: autoria de obras clássicas, gêneros, instrumentos, movimentos artísticos.
- **Língua e uso**: ortografia, significado de expressão idiomática, diferença entre dois termos
  próximos.

**Proporção de idioma**: 48 pt-BR e 12 en, para não deslocar o mix atual (0,80/0,20).

Alerta de colisão: `data/eval/testset.jsonl` tem justamente perguntas desse tipo, e já existem 9
colisões exatas no corpus. Nenhum enunciado deste grupo pode repetir um de lá — confira antes de
entregar.

---

## Grupo I — camada C (50 exemplos)

Conversa: desabafo, comemoração, nostalgia, opinião, criatividade curta, papo sobre gosto pessoal,
pergunta dirigida ao próprio assistente. Sem tool, sem cálculo, `<think>` ≤ 20 palavras. Tom
natural, resposta que soa como alguém conversando — não um laudo com tópicos e negrito.

Distribua, 10 de cada:
- **Desabafo e cotidiano** (trabalho puxado, cansaço, mudança de cidade, rotina).
- **Comemoração e boa notícia** (formatura, contratação, projeto que deu certo).
- **Nostalgia e memória afetiva** (música, jogo, lugar, comida da infância).
- **Opinião e discussão leve** (preferência entre duas coisas, "vale a pena X?", debate cultural).
- **Perguntas ao assistente** (o que você acha, você se cansa, qual seu tipo de problema favorito).

### Duas regras específicas, ambas por defeito observado

**1. Fato dentro de conversa continua sendo fato.** Na comparação de 2026-07-27 o modelo afirmou,
sobre polígonos regulares, que hexágonos são os **únicos** que pavimentam o plano — falso, triângulo
equilátero e quadrado também pavimentam — e citou "cascas de melancia" formando esse padrão, o que
não existe. Vinha embalado em tom simpático de curiosidade, e o tom não desculpa o erro. Regra: se
a frase contém uma afirmação de unicidade, exclusividade, superlativo ou "só/apenas/único", ela tem
de ser verdadeira, ou a frase não entra. Onde houver fato, ele é verificável — o `batch_015` já
teve de corrigir exatamente isso.

**2. Nada de estrutura de relatório.** Camada C não leva headers, listas numeradas, negrito em cada
segundo termo nem seção de conclusão. Um parágrafo ou dois, do jeito que uma pessoa responde.

**Proporção de idioma**: 40 pt-BR e 10 en.

---

## Grupo J — camada 0.5 (25 exemplos)

A pergunta **parece** exigir busca — menciona placar, preço, data, "este ano", "atual", nome de
evento — mas a resposta é estável, histórica ou fixa, e nenhuma tool é necessária.

**Formato obrigatório, que o validador mede**: rationale no primeiro parágrafo em **≤ 25 palavras**,
linha em branco, resposta no parágrafo seguinte. O `<think>` também fica em ≤ 25 palavras.

O rationale explica por que não precisa buscar, e precisa variar o fraseado — o filtro de 6-gramas
(`ngram_max_freq: 3`) roda justamente sobre as camadas 0.5 e 1. Mínimo de 10 formulações distintas
no grupo.

Tipos a cobrir:
- **Resultado histórico encerrado** (quem ganhou uma Copa antiga, quem escreveu uma obra, quando
  caiu um muro) — parece placar/notícia, é fato fechado.
- **Constante e definição com cara de dado atual** (velocidade da luz, número de ossos do adulto,
  quantidade de estados de um país).
- **Regra fixa vestida de "atual"** (quantos jogadores em campo, quantas cartas num baralho,
  duração de um tempo de jogo).
- **Pergunta com marcador temporal irrelevante** ("qual é a capital do Japão hoje?", "quantos
  planetas tem o sistema solar este ano?") — o marcador não muda a resposta.

**Cuidado com a fronteira**: o histórico do `batch_012`/`batch_013` mostra que reforçar a 0.5 sem
cuidado derrubou o recall de `web_search` de 0,75 para 0,35 — o modelo generalizou "não preciso
buscar" para casos que exigiam busca. Nenhum exemplo deste grupo pode ter rationale genérico do
tipo "isso eu já sei"; o motivo tem de ser a **propriedade do dado** (é histórico encerrado, é
constante física, é regra codificada), nunca a confiança do modelo em si mesmo.

**Proporção de idioma**: 20 pt-BR e 5 en.

---

## Formato de saída

Uma linha JSON por exemplo, sem markdown em volta, idêntico aos lotes anteriores:

```json
{"layer": "0", "lang": "pt-BR", "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "<think>\n...\n</think>\n\n..."}]}
```

Nenhum exemplo deste lote tem `role: tool` — não há tool call em camada 0, 0.5 ou C.

Sugestão de arquivos: `data/raw/gen/batch_046.jsonl` (grupo H), `batch_047.jsonl` (grupo I),
`batch_048.jsonl` (grupo J).

---

## Checklist antes de aceitar

1. Camada 0: preâmbulo de zero palavras, nenhum marcador de rationale, nenhuma tool call,
   `<think>` ≤ 15 palavras.
2. Camada 0.5: rationale no 1º parágrafo ≤ 25 palavras, linha em branco, resposta depois;
   `<think>` ≤ 25 palavras; motivo ancorado na propriedade do dado, não na confiança do modelo.
3. Camada C: `<think>` ≤ 20 palavras, sem estrutura de relatório, e todo fato afirmado é
   verdadeiro — com atenção redobrada a "único/só/apenas/o maior".
4. Nenhuma gíria da lista de `configs/gen_config.yaml` (`mano`, `véi`, `top demais`, `brabo`,
   `cringe`, `tipo assim`).
5. Nenhuma abertura ou transição repetida mais de 3 vezes no lote.
6. Zero colisão com `data/eval/testset.jsonl` e `data/eval/math_rigor_testset.jsonl` — o corpus já
   carrega 9 colisões herdadas; não aumente esse número.
7. Mix de idioma do lote fechando em 108 pt-BR / 27 en.

Ao final, rodar a validação completa e conferir a distribuição no `report.json`:

```bash
python src/validate_data.py data/raw/gen/batch_*.jsonl data/raw/pilot.jsonl data/raw/gpt56_combined_selection.jsonl
```

Esperado: camada C ≥ 0,16 e camada 0 ≥ 0,15. Se a camada C ficar abaixo de 0,15, o lote não
cumpriu o objetivo e precisa de mais exemplos do grupo I antes do treino.
