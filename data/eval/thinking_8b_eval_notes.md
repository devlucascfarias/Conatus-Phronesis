# Notas de avaliação — Qwen3-8B + thinking (branch `phronesis-thinking`)

Registro dos resultados da primeira rodada de treino real (860 exemplos, `<think>`
calibrado por camada), pra comparar contra a rodada com `do_sample=True` (parâmetros
recomendados do Qwen3) quando ela terminar.

## Setup desta rodada

- Modelo: `Qwen/Qwen3-8B`, adapter `outputs/adapter_8b`, `enable_thinking=True`.
- Decodificação: `do_sample=False` (greedy), `no_repeat_ngram_size=8`,
  `repetition_penalty=1.15` (adicionado nesta rodada especificamente pra testar se
  resolvia o loop de repetição — ver conclusão abaixo).
- Dois conjuntos testados: (1) bateria manual de 9 perguntas (`perguntas_avaliacao` no
  notebook, inclui os 3 casos que já tinham falhado ao vivo antes do `batch_022`), e
  (2) bateria manual à parte de 16 perguntas (célula escrita pelo usuário, não é o
  arquivo `data/eval/math_rigor_testset.jsonl` — são perguntas próprias de nível
  similar em computação/matemática/física, sem gabarito de referência no repositório;
  os vereditos abaixo vêm de conferência manual, não de comparação automática).

## Resultado 1 — bateria de 9 perguntas (regressão + amostra geral)

| # | Pergunta | Veredito |
|---|---|---|
| 1 | 37,5% de 18.420 | Parcial — número certo (6.907,5), mas inventa "R$" (pergunta não menciona dinheiro) |
| 2 | Dólar hoje | Falha — `<think>` alucina "duas primeiras buscas" e "uma terceira" quando só 1 resultado veio; tenta `requests.get()` direto (sandbox não tem rede) |
| 3 | Curiosidade sobre polígonos regulares | OK — dodge inteligente (heptadecágono de Gauss), evita a armadilha do ângulo de 1000 lados |
| 4 | 62,5% de 4.960 | Falha — bug do `//` voltou (`4960 * 5 // 8`, sem erro visível porque é divisão exata) + mesma alucinação de "R$" |
| 5 | Quem venceu o jogo do Brasil ontem | Falha — busca real trouxe só "Brasil 3x0 Haiti", resposta inventa "Japão e Escócia também venceram" |
| 6 | Segundo maior planeta | OK |
| 7 | Presidente do Brasil na Copa de 94 | Parcial — factualmente certo (Itamar Franco), mas frase final gramaticalmente quebrada |
| 8 | Pizza com abacaxi | OK |
| 9 | Bhaskara 2x²-11x+12=0 | OK — matemática certa (raízes 4 e 3/2), só um glitch de LaTeX (`\±`) |

## Resultado 2 — bateria manual de 16 perguntas (computação/matemática/física, sem gabarito no repo)

| # | Tema | Veredito |
|---|---|---|
| 1 | Complexidade merge sort com slices | OK |
| 2 | Estabilidade numérica sqrt(x²+1)-x | **Falha de derivação** — "forma equivalente" misturando x²+1, x²+2, x²+3 é inventada, não é identidade válida |
| 3 | GIL / threading / Lock | OK |
| 4 | Bellman-Ford vs Dijkstra | OK (typo leve: "ciclose") |
| 5 | Cache locality row-major | OK |
| 6 | Autovalores/exp(tA), matriz Jordan | **Falha grave** — conclui "A−4I é nula" (falso: é matriz de Jordan, não diagonalizável) e entra em loop de ~60 linhas trocando o autovalor a cada linha, nunca fecha |
| 7 | Integral dupla com substituição u,v | OK — conferido à mão, resultado exato bate: 8/3·sinh(1) |
| 8 | EDO com ressonância, IVP | **Falha grave** — erro na derivação da particular, tenta se corrigir 5 vezes, nunca fecha, texto vira "o que está errado?" repetido |
| 9 | Convergência de série (log(1-x)) | OK |
| 10 | Bayes/sensibilidade de teste | Parcial — sandbox devolve 2994 FPs corretamente, mas `<think>` seguinte troca pra "1994" (número fabricado) e a resposta final usa esse número errado |
| 11 | Esfera deslizando em cúpula | OK — conferido à mão, cosθ=2/3 está certo |
| 12 | Osciladores acoplados, modos normais | **Falha de física** — conclui que os dois modos têm a mesma frequência (errado: deveriam ser ω₁=√(k/m) e ω₂=√(3k/m), diferentes) |
| 13 | Campo elétrico, esfera não uniforme | **Falha grave** — expressões inconsistentes dentro do próprio texto (r⁴/R⁴ tratado como igual a r⁴/R³), código quebra (`sp.Epsilon_0` não existe), tenta chamar tool **"python"** que não existe, `</think>` duplicado e mal formado |
| 14 | Ciclo termodinâmico | **Falha de física** — alucina uma inconsistência no ciclo que na verdade fecha certo (conferido: T_C=T_A, consistente), "corrige" o problema errado, aceita eficiência de **131%** sem questionar (fisicamente impossível) |
| 15 | Dilatação temporal relativística | OK — conferido, γβ≈4,90 está certo |
| 16 | Partícula em caixa, incerteza ΔE | **Falha grave** — erro de álgebra na normalização (esquece de dividir por 5), chega a resultado imaginário, entra em loop repetindo "a incerteza é zero" ~15x com erros de grafia crescentes, resposta final ΔE=0 está **errada** (valor real ≈1,2·E₁, não zero) |

**Contagem**: 8/16 corretos, 4/16 falha grave com colapso em loop, 4/16 falha de derivação/física sem loop (mas resposta final errada ou não confiável).

## Efeito do `repetition_penalty=1.15`

**Não resolveu.** Os 4 itens que colapsavam em loop antes (6, 8, 13, 16) saíram
praticamente idênticos com o penalty aplicado. Hipótese confirmada: o loop não repete
o mesmo token — repete a **estrutura da frase trocando um número a cada linha**
("...iguais a **3**...exp3tI" → "...iguais a **5**...exp5tI"), então grande parte do
texto nunca conta como "token repetido" pro mecanismo de penalidade enxergar.
`no_repeat_ngram_size=8` tem o mesmo problema pelo mesmo motivo.

## Padrões identificados (para ação futura)

1. **Colapso em loop de repetição** (camada 3, quando a autocorreção falha mais de uma
   vez) — não resolvido por ajuste de decodificação. Hipótese principal: o dataset só
   ensina autocorreção que funciona de primeira; nunca há exemplo de "ainda não fechei
   depois de tentar de novo, respondo com ressalva". Provável necessidade de dado novo
   (exemplos de desistência graciosa/bounded retry), não só mais épocas.
2. **Fabricação de dado fora da fonte generalizou** além dos 3 casos que o `batch_022`
   corrigiu — apareceu em cenários novos (jogo do Brasil, contagem de FPs do Bayes).
   Sugere que a correção precisa ser a regra geral ("nunca cite/use número que não veio
   do `tool_response`"), reforçada em mais variações, não só os casos memorizados.
3. **Bug do `//` resurgiu** numa pergunta nova (62,5% de 4.960) — o padrão ainda não
   generalizou de forma robusta apesar de 3 lotes corretivos (018, 020, 022) endereçando
   variações dele.
4. **Alucinação de unidade** ("R$" sem contexto de dinheiro) persiste em 2/2 casos de
   porcentagem testados nesta rodada, apesar do contraste explícito no `batch_022`
   (itens 1210/1211).
5. **Erros de física/matemática reais**, não só de formato: osciladores acoplados
   (frequências erradas), ciclo termodinâmico (eficiência >100% aceita sem questionar),
   campo elétrico (auto-contradição na própria derivação).

## Resultado 3 — mesma bateria de 16, agora com `do_sample=True`

`temperature=0.6`, `top_k=20`, `top_p=0.95`, `repetition_penalty=1.15`,
`no_repeat_ngram_size=8` (confirmado no `generation_config.json` real do Qwen3-8B).

| # | Tema | Greedy (antes) | Sampling (agora) |
|---|---|---|---|
| 1 | Complexidade merge sort | OK (Θ(n log n) tempo e espaço) | Parcial — espaço dado como Θ(n) (provavelmente errado, deveria ser Θ(n log n)); tool call não verifica nada de verdade |
| 2 | Estabilidade numérica sqrt(x²+1)-x | Falha de derivação (identidade inventada) | Derivação **melhor** (1/(√(x²+1)+x), correta) mas código quebra 2x seguidas (string não fechada, sintaxe malformada) — nunca entrega a função pedida |
| 3 | GIL / threading / Lock | OK | OK |
| 4 | Bellman-Ford vs Dijkstra | OK | OK |
| 5 | Cache locality | OK | OK (com exagero não verificado: "mil vezes mais rápido"; alega TLB miss igual nos dois casos, questionável) |
| 6 | Autovalores/exp(tA) | **Falha grave** — "diagonalizável" (errado) + loop de ~60 linhas | **Método certo dessa vez** (decomposição de Jordan, conclui corretamente "não diagonalizável"), mas tangente sem sentido tentando λ=3 primeiro, e a matriz final de exp(tA) tem erro de digitação/álgebra |
| 7 | Integral dupla u,v | **OK** (conferido: 8/3·sinh(1)) | **Regressão — errado com confiança**: alega o integrando é ímpar em v (falso) e conclui que a integral vale 0, sem nenhuma verificação |
| 8 | EDO com ressonância | Falha grave (loop "o que está errado?") | Não entra em loop, mas divaga em álgebra sem sentido, chama tool inexistente (`python_jupyter_cell`), nunca fecha com resposta final |
| 9 | Convergência de série | OK | Conclusão majoritariamente certa, mas se autocontradiz no fim (diz que converge pontualmente em x=1, quando a própria explicação anterior mostrou que diverge ali) |
| 10 | Bayes/sensibilidade | Falha — fabrica "1994" do nada | **Melhor** — sem número fabricado, chega em ~15 falsos por verdadeiro (correto ≈15,3), mesmo com um deslize (usa 98.000 em vez de 99.800 na população saudável) |
| 11 | Esfera deslizando em cúpula | **OK** (conferido: cosθ=2/3) | **Regressão — errado com confiança**: erro de sinal na álgebra, chega em "sinθ=3/5" (não segue nem da própria equação escrita) |
| 12 | Osciladores acoplados | Falha (conclui frequências iguais) | Ainda errado, mas ao menos reconhece que as frequências deveriam ser diferentes; usa uma matriz numérica inventada sem relação com o sistema físico real |
| 13 | Campo elétrico | Falha grave (tool "python" inexistente, `</think>` malformado) | Ainda falha — mais nomes de tool inventados (`python_sandro`), variável não definida, código quebrado, nunca fecha |
| 14 | Ciclo termodinâmico | Falha — alucina inconsistência que não existe, aceita eficiência de 131% | **Melhoria real**: reconhece corretamente que o ciclo FECHA (T_B=2T0, T_C=T0, T_A=T0 — bate com a conferência manual) — mas o código final é nonsense (usa `input()` dentro do sandbox, que não faz sentido ali) e nunca entrega números |
| 15 | Dilatação temporal relativística | **OK** (conferido: γβ≈4,90) | **Regressão — errado com confiança**: calcula β=0,8 (deveria ser √(24/25)≈0,98), resultado final incorreto (4cτ₀ em vez de ~4,9cτ₀), e a "previsão sem dilatação" sai com unidade sem sentido |
| 16 | Partícula na caixa, incerteza | Falha grave (loop "incerteza é zero" ~15x) | Não entra em loop, mas erra a normalização desde o primeiro passo (esquece metade do termo), chega em P₁=P₂=1/2 (deveria ser 1/5, 4/5 — isso é dado quase direto pelo enunciado) e numa resposta final com unidades inconsistentes |

### Veredito da comparação

**O loop de repetição sumiu por completo (0/16 com sampling, contra 4/16 no greedy)** —
sampling resolve estruturalmente esse problema, confirmando a hipótese.

**Mas surgiu uma troca ruim: respostas erradas COM confiança, sem nenhum sinal de
alerta.** Três itens que o greedy acertou (7, 11, 15) o sampling errou de forma
fluente e assertiva — sem repetição, sem "o que está errado?", só uma resposta limpa
e incorreta. Isso é mais perigoso que o loop: o loop pelo menos é obviamente quebrado
pra quem estiver lendo; uma resposta errada bem escrita passa despercebida.

**Chamada de tool inexistente piorou**: 4 nomes inventados diferentes só nesta rodada
(`python_jupyter_cell`, `python_print`, `python_eval`, `python_sandro`/`python_sandox`),
contra 1 no greedy (`python`). Código com erro de sintaxe também ficou mais frequente.

**Contagem aproximada**: greedy = 8 certos / 4 loop-quebrado / 4 errado-sem-loop.
Sampling = ~5 certos / 0 loop / ~7 errado-com-confiança / 4 nunca fecha (código quebra
antes de chegar a uma resposta, mas sem virar lixo repetitivo).

### Conclusão prática

Nenhum dos dois modos de decodificação é "a solução". `repetition_penalty` +
`no_repeat_ngram_size` sozinhos (greedy) não bastam contra o colapso em loop; sampling
resolve o loop mas piora confiabilidade de tool-calling e introduz erros silenciosos.
Isso reforça a hipótese de dado (não decodificação) como causa raiz: o modelo precisa
de mais exemplos de (a) verificação real via tool antes de assumir um resultado como
final — vários dos erros "confiantes" da rodada de sampling (7, 11, 15) nunca chamaram
`python_sandbox` pra conferir, foram direto pro `\boxed{}` sem checagem — e (b)
desistência graciosa quando a autocorreção não fecha, em vez de degenerar (greedy) ou
inventar uma resposta plausível sem verificar (sampling).
