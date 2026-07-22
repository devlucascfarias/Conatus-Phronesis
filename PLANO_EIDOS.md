# Conatus Eidos — agente CLI especialista em frontend

> Branch nova (`conatus-eidos`) herdando a infraestrutura do Conatus-Phronesis.
> Missão: um modelo pequeno que trabalha como agente de terminal em projetos frontend
> (React + Next + Tailwind), com disciplina de CLI e gosto visual — não um generalista.

## Tese (herdada e comprovada no projeto anterior)

Modelo pequeno + poucos exemplos aprende **critério e ritual, não conhecimento**.
O conhecimento de React/CSS vem do modelo base (coder pré-treinado); o nosso SFT ensina:

1. **O ciclo editar → rodar → ler erro → corrigir** (coração do dataset, decisão do sócio).
   Nenhum base tem essa disciplina de fábrica; é verificável por execução real.
2. **Ritual de terminal**: instalar antes de importar, buildar depois de editar, ler o
   stderr inteiro antes de reagir, não repetir comando que acabou de falhar sem mudar algo.
3. **Gosto visual como assinatura**: espaçamento, tipografia, estados (hover/focus/disabled),
   dark mode, acessibilidade básica — o padrão "elegante e moderno" consistente.
4. **Julgamento**: quando editar arquivo vs rodar comando vs admitir que precisa de contexto.

## Decisões tomadas (2026-07-22)

- **Base:** Qwen3-Coder ~7B para a primeira rodada; reavaliar tamanho depois.
  ⚠️ VERIFICAR NA FASE 0 qual checkpoint existe de fato nesse porte: candidatos são
  `Qwen2.5-Coder-7B-Instruct` (denso, comprovado) e `Qwen3-Coder-30B-A3B-Instruct`
  (MoE, 3B ativos — pesado pra VRAM do Colab mesmo em 4-bit). Escolher o que couber
  no QLoRA do Colab com folga; não assumir que "Qwen3-Coder-7B" existe sem checar.
- **Stack única:** React + Next + Tailwind. Dashboards e landing pages são casos de uso
  desse recorte, não escopos separados. Expandir stack só depois de uma versão entregue.
- **Prioridade nº 1 do dataset:** o ciclo de correção com feedback do terminal.

## Ferramentas do universo do agente

| Tool | Assinatura | Notas |
|---|---|---|
| `read_file` | `(path)` | conteúdo com números de linha |
| `write_file` | `(path, content)` | cria/sobrescreve |
| `edit_file` | `(path, old, new)` | substituição exata (mais barato em tokens que write) |
| `run_terminal` | `(command)` | stdout+stderr crus, cwd do projeto; timeout; whitelist (npm/npx/node/next/git status/ls/cat) |

Mesmo formato nativo de tool call do Qwen (`<tool_call>...</tool_call>`), mesmo parser
(`common.extract_tool_calls`) — a infra do Phronesis serve inteira.

## Fases (eval antes de dados — lição nº 1 do projeto anterior)

### Fase 0 — Harness de eval + baseline (ANTES de qualquer exemplo)
- **Projeto-template**: um app Next + Tailwind mínimo versionado em `eidos/template_app/`
  (com `node_modules` cacheado no Colab/máquina via `npm ci` uma vez — build do zero a cada
  caso é inviável; o validador copia o template e aplica o caso por cima).
- **~100 casos de teste** em 4 famílias, cada um com **verificação automática**:
  1. `fix-build` (~30): projeto com erro plantado (import errado, tipo errado, JSX quebrado,
     dependência faltando) → métrica: `next build` volta a passar em ≤ N iterações de tool.
  2. `fix-visual` (~20): bug de CSS/layout descrito em texto (ex.: "o botão vaza do card
     no mobile") → métrica: assert estrutural no JSX/classes (grep dirigido por caso) +
     build passa. (Screenshot-diff fica pra v2 — caro demais na v1.)
  3. `create-component` (~30): "crie um card de métrica com título, valor e variação
     percentual" → métrica: arquivo criado, build passa, asserts de conteúdo (usa Tailwind,
     exporta default, props tipadas, tem estado hover/dark).
  4. `terminal-ops` (~20): "instala o recharts e cria um gráfico de linha básico" →
     métrica: comando certo executado, dependência no package.json, build passa.
- **Métricas agregadas**: taxa de sucesso por família, nº médio de iterações até o verde,
  taxa de "reagiu ao stderr" (mudou algo após erro vs repetiu cegamente), tool call JSON
  válido, e taxa de alucinação de API (importar o que não existe).
- **Rodar o baseline do coder cru** neste harness. Só o gap observado dita o dataset.

### Fase 1 — Piloto (~20 exemplos à mão)
Mesmo processo do Phronesis: escrever manualmente, revisar tom e formato, aprovar antes
de escalar. Definir aqui o **guia de estilo visual** (o "gosto" vira checklist objetivo:
tokens de espaçamento, escala tipográfica, dark mode por padrão, transitions discretas).

### Fase 2 — Geração + validação executável
- Gerador segue `prompts/` novo (`generator_eidos.md`), com camadas (abaixo).
- **Validador executa de verdade**: aplica o exemplo no template, roda os comandos do
  exemplo, confere que o stdout/stderr do turno `tool` BATE com a execução real (o
  equivalente do check da camada 2 do Phronesis, agora com npm/tsc — mais lento, então
  cache agressivo do template e paralelismo limitado).
- Alvo inicial: ~300-400 exemplos (mesma escala que funcionou), NÃO mais.

### Camadas do dataset (proposta, calibrar na Fase 1)

| Camada | Comportamento | Share alvo |
|---|---|---|
| E1 | Ciclo completo: editar → `run_terminal` (build/lint) → erro → ler → corrigir → verde | 30% |
| E2 | Criação de componente/página com o guia de estilo, build verde de primeira | 25% |
| E3 | Operações de terminal com julgamento (instalar, scaffold, scripts) | 15% |
| E4 | Diagnóstico sem edição: ler erro/arquivo e explicar a causa antes de agir | 10% |
| E5 | Fronteiriça: quando NÃO agir (pedir contexto, recusar comando destrutivo, não reinstalar o que já existe) | 10% |
| EC | Conversa técnica natural (revisão de abordagem, trade-offs, papo de dev) | 10% |

Lições anti-whack-a-mole herdadas: nunca deixar uma camada passar de ~30%, vigiar a EC
(a conversa foi o que quebrou primeiro no Phronesis), lotes corretivos pequenos e dirigidos.

### Fase 3 — Treino (QLoRA, notebook adaptado do atual)
### Fase 4 — Eval no harness da Fase 0 + análise de erro
### Fase 5 — Demo real: o agente consertando um projeto Next de verdade no Colab/local

## Riscos conhecidos (declarados antes de começar)

1. **Custo do validador**: cada exemplo com build real custa segundos-minutos. Mitigação:
   template cacheado, `tsc --noEmit` como verificação rápida (build completo só na eval).
2. **Geração longa**: código é 10-50x mais tokens que os rationales do Phronesis; treino
   mais caro por exemplo e `max_new_tokens` maior na inferência. Orçar na Fase 0.
3. **O gosto visual é subjetivo**: vira checklist objetivo na Fase 1 ou vira ruído no dataset.
4. **Deriva de ecossistema**: versões de Next/Tailwind mudam; fixar versões no template e
   declarar no model card ("treinado contra Next X.Y, Tailwind Z").
5. **Teto do 7B**: erros semânticos que compilam limpo vão existir (aprendido no Phronesis,
   limitação 6). O harness pega o que executa errado; o resto é documentação honesta.

## Próximo passo imediato

Fase 0: montar `eidos/template_app`, escrever os ~100 casos de eval com seus checks,
e rodar o baseline do coder escolhido. Nada de dataset antes disso.
