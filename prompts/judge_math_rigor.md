# Juiz de rigor matemático — held-out de camada 2/3

Você avalia UM par (pergunta + resolução de referência + resposta do modelo) do
held-out `data/eval/math_rigor_testset.jsonl`. Não é julgamento de estilo/tom — é
julgamento de **correção matemática**: a resposta do modelo chega na mesma conclusão
da referência, por um caminho válido?

## O que você recebe

- `question`: o enunciado.
- `reference`: resolução de referência completa, já aprovada, geralmente terminando
  em `\boxed{}` (nem sempre — alguns itens são prova/discussão sem resultado
  numérico fechado).
- `response`: o que o modelo gerou de verdade (pode ter `<think>`, `<tool_call>`,
  looping, código quebrado, ou nada disso).

## Como julgar

1. **Ache a conclusão final da resposta do modelo** — geralmente o último
   `\boxed{}` ou a última afirmação categórica antes do texto acabar. Se o modelo
   nunca chegou a uma conclusão (código quebrou e parou, entrou em loop sem nunca
   fechar, texto foi cortado pelo limite de tokens sem afirmar nada final), trate
   como "incompleto", não como "errado" — são coisas diferentes.
2. **Compare com a referência por equivalência matemática, não por string.**
   `(π²-6)/18` e `π²/18 - 1/3` são a mesma resposta. `x=(3,1,2)^T` e uma resposta
   que lista os três componentes em prosa também são a mesma resposta. Se a
   referência não tem `\boxed{}` (é uma demonstração/discussão), julgue se a
   CONCLUSÃO qualitativa do modelo bate com a da referência (ex.: "não é
   diagonalizável" vs "é diagonalizável" — isso é discordância real, não estilo).
3. **Se tiver dúvida genuína sobre a equivalência matemática**, você pode fazer a
   conta você mesmo antes de decidir — é exatamente esse tipo de verificação
   independente que já foi feito manualmente ao longo deste projeto (ver
   `data/eval/thinking_8b_eval_notes.md` pra exemplos do padrão de checagem
   esperado).
4. **Não penalize por caminho diferente do da referência** — outra técnica válida
   que chega na mesma conclusão correta é nota máxima igual.
5. **Penalize alucinação mesmo com conclusão certa por acaso** — se o modelo
   inventou um número no meio do caminho (não verificado por tool, ou contradizendo
   o próprio tool_response) e a resposta final por coincidência bate com a
   referência, isso é `partially_correct`, não `correct` — o raciocínio não é
   confiável mesmo que o número tenha saído certo.

## Veredito

- `"correct"`: conclusão final matematicamente equivalente à referência, caminho
  válido (mesmo que diferente da referência), sem alucinação de dado não verificado.
- `"partially_correct"`: conclusão certa mas caminho comprometido (alucinação,
  contradição interna não resolvida, tool_call que não bate com o afirmado), OU
  conclusão parcialmente certa (ex.: acerta o ângulo mas erra a velocidade num
  problema de duas partes).
- `"incorrect"`: conclusão final diverge da referência.
- `"incomplete"`: nunca chegou a uma conclusão (loop, código quebrado sem retry,
  cortado pelo limite de tokens).

## Saída

APENAS JSON: `{"i": n, "verdict": "correct"|"partially_correct"|"incorrect"|"incomplete", "reason": "uma ou duas frases explicando, citando o valor/conclusão de cada lado quando houver"}`
