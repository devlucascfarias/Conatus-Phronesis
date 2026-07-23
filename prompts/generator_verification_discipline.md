Você vai gerar exemplos de treino NOVOS (não é retrofit de item existente) pra um
dataset SFT de um modelo pequeno com tool-use (web_search, python_sandbox) e
raciocínio em `<think>`. Objetivo: corrigir dois padrões de falha reais, medidos
numa avaliação pós-treino documentada em `data/eval/thinking_8b_eval_notes.md` —
leia esse arquivo inteiro antes de começar, ele tem a evidência completa.

## Os dois padrões que você vai ensinar

### Padrão 1 — "nunca fecha sem verificar"

Na avaliação com `do_sample=True`, o modelo chegou a `\boxed{}` errado em pelo menos
3 itens (integral dupla, esfera deslizando numa cúpula, dilatação temporal
relativística) SEM NUNCA chamar `python_sandbox` antes — foi direto da dedução em
prosa pro resultado final. Nos três casos a conta tinha erro de sinal/álgebra que o
sandbox teria pego na hora. Isso é pior que os casos que erravam com `//` (bug já
conhecido): aqui não tem sinal de alerta nenhum, a resposta lê como se fosse
confiável.

**Regra a ensinar**: toda afirmação numérica em camada 2 ou 3 — resultado de
integral, raiz de equação, valor de ângulo, razão entre grandezas, o que for — passa
por `python_sandbox` (numérico ou simbólico, o que fizer sentido pro problema) antes
do `\boxed{}` final. Não é sobre desconfiar de tudo sempre — é sobre nunca pular a
checagem só porque a conta "parece" ter fechado limpo.

### Padrão 2 — "desistência graciosa" (não existe hoje no dataset)

Quando a autocorreção falha mais de uma vez, o modelo hoje só tem dois destinos: (a)
greedy — entra num loop reescrevendo a mesma conclusão trocando um número a cada
linha, nunca fecha (visto em 4/16 itens do held-out); ou (b) sampling — inventa uma
resposta plausível sem verificar, confiante e errada (visto nos 3 casos do Padrão 1).
Isso acontece porque **todo exemplo de autocorreção no dataset atual mostra a
correção funcionando de primeira** — não existe exemplo de "ainda não fechei depois
de tentar de novo".

**Comportamento a ensinar**: depois de UMA tentativa de correção que ainda não bateu
com o checker (ou que ainda deixa uma inconsistência visível), o modelo para,
reconhece explicitamente que não conseguiu fechar com confiança total, e entrega o
melhor resultado que tem — com a ressalva clara — em vez de tentar de novo
indefinidamente ou inventar um número novo sem checar. Isso é uma habilidade nova,
diferente da autocorreção "de primeira tentativa" que já existe (`self_correction` em
`configs/gen_config.yaml`).

## O que gerar

**50 itens novos**, salvos em `data/raw/gen/batch_023.jsonl`, `task_id` sequencial a
partir de 1301.

- **28 itens do Padrão 1** (verificação antes de fechar), camada 2 majoritariamente
  (uns 8 de camada 3), em temas VARIADOS — não repita os mesmos 3 problemas que
  falharam na avaliação, generalize pra dezenas de contextos diferentes (geometria,
  trigonometria, cálculo, probabilidade, física básica e avançada, etc.). Cada item:
  resolução em prosa/LaTeX termina com `<tool_call>` de `python_sandbox` que
  verifica o resultado ANTES de qualquer `\boxed{}` aparecer no texto. Formato: nunca
  afirme o valor final e DEPOIS chame a tool pra "confirmar" — a tool vem primeiro, o
  `\boxed{}` só aparece depois do retorno dela.

- **22 itens do Padrão 2** (desistência graciosa), misturando camada 2 (uns 14) e
  camada 3 (uns 8). Estrutura de cada item:
  1. Assistant tenta resolver, comete um erro plausível (sinal trocado, termo
     esquecido, fórmula certa aplicada errado).
  2. Chama `python_sandbox` pra checar — o checker discorda.
  3. Assistant reconhece o erro, tenta corrigir — **mas a segunda tentativa
     TAMBÉM não fecha** (outro erro, ou o checker ainda diverge, ou a verificação
     cruzada não bate). Isso é o ponto central: a correção tem que genuinamente
     falhar de novo, não ser um segundo erro cosmético fácil de resolver.
  4. Assistant reconhece explicitamente, numa frase, que não conseguiu fechar com
     certeza total depois de duas tentativas — e entrega o valor mais confiável que
     tem (geralmente o do último checker, mesmo que a derivação analítica não bata
     100%), com uma ressalva curta e honesta. Nunca dramático, nunca se desculpando
     demais — o mesmo tom "sem drama" que já rege a autocorreção normal em
     `prompts/generator_system.md`.
  5. Turno `tool` é sempre execução real — nunca fabricar stdout (mesmo invariante
     de sempre).

## Formato e regras que já valem (não repetir aqui, só seguir)

Tudo de `prompts/generator_system.md` continua valendo: schema JSONL exato, `<think>`
obrigatório em todo turno assistant com o teto de palavras por camada
(`configs/gen_config.yaml` → `think_max_words`), tom de voz, variação de abertura
(sem frase-fôrma — mesma disciplina que já foi auditada por n-grama nas rodadas
anteriores, ver `data/eval/thinking_8b_eval_notes.md`), LaTeX consistente.

**Atenção extra pro Padrão 2**: o `<think>` de cada turno precisa refletir o estado
real da deliberação naquele momento — no turno onde a segunda tentativa também
falha, o `<think>` reconhece isso ANTES da resposta visível verbalizar a
desistência (não é forçado; é o julgamento genuíno de "essa segunda tentativa também
não fechou, o que eu faço agora").

**Nomes de tool exatos, sempre**: `python_sandbox` e `web_search`, exatamente como em
`configs/tools.json`. A avaliação recente mostrou o modelo inventando nomes
(`python_jupyter_cell`, `python_eval`, `python_print`, `python_sandro`) — isso não
pode aparecer nos exemplos de treino de jeito nenhum; confira cada `<tool_call>`
contra o schema antes de aceitar.

## Auditoria antes de entregar

Mesma disciplina das rodadas anteriores:
1. Rode um script de n-gramas (6 palavras) no `<think>` dos 50 itens novos CONTRA o
   corpus inteiro já existente (pilot, gen/batch_0XX, gpt56_*) — zero repetição
   acima de frequência 3, mesmo padrão já validado antes.
2. Confira que todo código Python dos itens de Padrão 1 e 2 realmente executa e o
   stdout bate com o que está escrito no turno `tool` — vou rodar
   `python src/validate_data.py` depois, que já faz essa reexecução real pra camada
   2, mas revise antes de me entregar.
3. Nos itens de Padrão 2, confirme que a segunda falha é genuína (não um erro fácil
   óbvio) e que a desistência não soa como desculpa — é uma frase de reconhecimento
   direto + o valor mais confiável disponível.

## Ao terminar

Rode:
    python src/validate_data.py data/raw/pilot.jsonl data/raw/gen/*.jsonl data/raw/gpt56_combined_selection.jsonl
    python -m pytest tests/test_thinking.py -q

Reporte: contagem por camada/padrão, saída real do teste de n-gramas, resultado da
validação e dos testes. Não toque em nenhum arquivo fora de `data/raw/gen/batch_023.jsonl`. Não faça commit.
