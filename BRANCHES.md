# Branches deste repositório — leia antes de commitar

Este repositório hospeda **dois projetos diferentes** que não têm nenhuma relação de
código entre si. Eles compartilham o mesmo repositório Git só por conveniência
histórica, mas vivem em branches separadas e **nunca devem ser misturados**.

## `main` — Conatus Phronesis (o modelo que importa aqui)

Modelo pequeno (Qwen3-4B-Instruct-2507, QLoRA) para tool-use calibrado: decidir quando
buscar na web, quando verificar cálculos num sandbox Python, quando só responder. É o
projeto descrito em `plano.md`, `MODEL_CARD.md`, `README.md`.

- `main` já tem um ciclo completo: dataset (`data/`), treino (`notebooks/train_colab.ipynb`),
  merge + quantização GGUF (`notebooks/phronesis_merge_quantize.ipynb`) — **o resultado
  desse merge é literalmente o `phronesis-4b` que roda no Ollama em produção**, servido
  pelo Conatus-UI.
- Todo commit relacionado a **dataset, prompts de geração (`prompts/generator_system.md`,
  `prompts/generator_math_gpt56.md`), configs de treino, ou o próprio notebook de treino**
  pertence a `main`.
- Antes de commitar qualquer coisa relacionada ao Phronesis, rode `git branch --show-current`
  e confirme que é `main`. Se não for, `git checkout main` primeiro.

## `conatus-eidos` — Conatus Eidos (projeto diferente, agente de código)

Agente de linha de comando especialista em frontend, baseado em **Qwen2.5-Coder-7B**
(depois Qwen3-Coder-30B-A3B como fork/Poiesis) — descrito em `PLANO_EIDOS.md`, vive
inteiro dentro de `eidos/`. Não usa `python_sandbox`/`web_search`, não tem relação com
matemática/física, não compartilha dataset nem prompts com o Phronesis.

- Todo commit relacionado a **episódios do Eidos (`eidos/data/batch_eNNN.py`), ao harness
  de avaliação do Eidos (`eidos/run_eval.py`), ou ao `template_app`** pertence a
  `conatus-eidos`.

## O incidente que motivou este arquivo

Em 2026-07-22, uma sessão inteira de destilação de dados pro Phronesis (466 exemplos de
matemática/física via GPT-5.6, batches de identidade e recall de busca, a decisão de
merge com o pipeline original, um eval de rigor matemático — 5 commits) foi commitada
em `conatus-eidos` por engano, simplesmente porque essa era a branch já ativa no working
directory no início da sessão (deixada assim de uma sessão anterior de trabalho no Eidos).

Ninguém percebeu até o usuário ir treinar o Phronesis a partir de `main` (o notebook
`train_colab.ipynb` faz `git clone`/`git pull` de `main` no Colab) — e `main` não teria
nenhum dos 5 commits. A destilação inteira teria ficado sem efeito no treino, silenciosamente,
sem nenhum erro ou aviso — o notebook rodaria normalmente, só que com o dataset antigo.

**Causa raiz**: nenhuma verificação de branch acontecia antes de commitar trabalho do
Phronesis. `git status`/`git diff` mostram o que mudou, mas não em qual branch aquilo faz
sentido logicamente — só `git branch --show-current` (ou ler `git log --oneline -3` e
reconhecer o projeto pelos commits recentes) pega isso.

**Correção aplicada**: os 5 commits foram identificados (confirmando primeiro que `main`
e `conatus-eidos` eram idênticos nos arquivos do pipeline de dataset antes da divergência,
via `git diff main $(git merge-base main conatus-eidos)`) e levados pra `main` via
`git cherry-pick`, sem rebase/force-push — `conatus-eidos` manteve o histórico duplicado,
sem perda de dado. Revalidado (579/579 aprovados) e reconstruído (`train.jsonl`) na branch
correta antes de confirmar o notebook como pronto.

## Regra prática daqui pra frente

Antes de qualquer `git commit` neste repositório, perguntar: **"esse arquivo é do
Phronesis ou do Eidos?"** — e conferir que `git branch --show-current` bate com a resposta.
Se a sessão começou numa branch por causa de trabalho anterior não relacionado ao que está
sendo feito agora, trocar de branch ANTES do primeiro commit, não depois.
