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
  (2) `data/eval/math_rigor_testset.jsonl` — 16 itens held-out de camada 2/3, nunca
  usados em treino, com resolução de referência.

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

## Resultado 2 — held-out `math_rigor_testset.jsonl` (16 itens, camada 2/3)

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

## Pendente — comparação com `do_sample=True`

Rodando com os parâmetros recomendados do `generation_config.json` real do Qwen3-8B
(confirmado, não estimado): `temperature=0.6`, `top_k=20`, `top_p=0.95`,
`repetition_penalty=1.15`, `no_repeat_ngram_size=8` mantidos.

**Preencher depois que a rodada terminar**: os mesmos 16 itens do held-out saem do loop
de repetição com sampling? Os erros de derivação/física (2, 12, 13, 14) mudam ou
persistem (esses não são sobre repetição, então sampling sozinho não deveria corrigi-los)?
