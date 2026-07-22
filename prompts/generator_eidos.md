# Spec do dataset Conatus Eidos — agente CLI frontend

Meta: **50 exemplos por camada × 6 camadas = 300 episódios**, dirigidos pelos achados do
baseline (0,06 de success_rate do Qwen2.5-Coder-7B cru nos 100 casos). Cada camada ataca
um sintoma medido, não uma suposição.

## Formato de um episódio

```json
{"layer": "L1", "lang": "pt-BR", "messages": [
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "<CoT técnico em texto plano>\n<tool_call>\n{\"name\": ..., \"arguments\": ...}\n</tool_call>"},
  {"role": "tool", "content": "<output REAL da execução>"},
  ...,
  {"role": "assistant", "content": "<resumo final, sem tool call>"}
], "_meta": {"scenario": "...", "batch": "e001"}}
```

- **Sem system prompt nos dados**: o trainer injeta o MESMO `SYSTEM_PROMPT` do
  `run_eval.py` + tools no chat template. Treino e eval veem a mesma distribuição.
- **Tool calls SEMPRE na tag `<tool_call>`** (sintoma 5 do baseline: o cru usa bloco
  ```json``` em 100% dos casos — cada exemplo é uma vacina de formato).
- **Outputs de tool são REAIS**: o builder (`build_episodes.py`) executa cada ação com os
  executores do próprio harness e grava o que voltou. Nada de output inventado — a lição
  da camada 2 do Phronesis, industrializada.
- Loss só nos turnos do assistant (máscara igual à do Phronesis).

## O CoT técnico (o que faz generalizar)

Todo turno de assistant com tool call segue o esqueleto, com redação VARIADA:
1. **Leitura da situação**: o que a tarefa pede / o que o último output diz — citando o
   dado concreto ("o tsc aponta TS2304 em Navbar.tsx:12: 'navLinks' não existe").
2. **Causa ou plano**: por que isso acontece / qual o próximo passo e por quê.
3. **Ação**: a tool call que materializa o plano.

O turno final resume o que foi feito E cita a verificação ("tsc saiu limpo — exit 0").
Proibido: CoT genérico ("vou analisar o problema"), passos que não usam o resultado
anterior, frase-fôrma repetida entre episódios.

## As 6 camadas (cada uma ↔ um sintoma medido no baseline)

| Camada | Sintoma no baseline | Comportamento-alvo | Share |
|---|---|---|---|
| **L1** ciclo completo | 97% do fix-build falha em "compila"; avg_iterations 0,93 | diagnosticar (tsc/build) → ler → editar → **re-verificar → repetir até exit 0** | 50 ex |
| **L2** entrega verificada | 43% do create-component nem cria o arquivo; 0% de sucesso | `write_file` com schema certo → tsc → verde → resumo. Componente COMPLETO no guia de estilo | 50 ex |
| **L3** investigação autônoma | 30% do fix-build pede pro usuário colar código | tarefa vaga → `read_file`/tsc PRIMEIRO; CoT verbaliza "tenho as ferramentas, não pergunto" | 50 ex |
| **L4** estilo completo | 95% das falhas do fix-visual são "conteúdo": edit parcial | CoT enumera TODAS as pendências do guia (checklist) antes do edit único e completo | 50 ex |
| **L5** recuperação de tool | 5 casos multi-ação sem arquivo criado; JSON/args malformados sem retry | erro de argumento/`old` ambíguo/comando bloqueado → ler o erro → corrigir a chamada | 50 ex |
| **LC** conversa técnica | vacina anti-estreitamento (lição Phronesis: conversa quebra primeiro) | papo de dev sem tool: trade-offs, revisão de abordagem, opinião técnica | 50 ex |

## Regras anti-contaminação e anti-colapso

- **NUNCA reusar os arquivos/bugs/prompts do `eval_cases.jsonl`** (é o testset). Mesmos
  *tipos* de habilidade, cenários novos — componentes, bugs e pedidos diferentes.
- Variar: nomes de componente, tipo de bug (TS2304/2322/2551/1005/JSX...), registro do
  usuário (formal/informal), tamanho do episódio (2 a 6 ações), pt-BR dominante com ~15% en.
- Nenhuma camada acima de ~30% do dataset final (lição anti-whack-a-mole).
- LC sem tool call NENHUM (o modelo precisa aprender quando NÃO agir).

## Pipeline

1. Cenários descritos em `eidos/data/batch_eNNN.py` (código: setup + CoTs + ações).
2. `build_episodes.py` executa cada cenário contra o template real, grava outputs
   autênticos, valida invariantes (tsc verde no fim das camadas de código, formato das
   tags, CoT não-vazio) e emite `eidos/data/episodes_eNNN.jsonl`.
3. Commit do `.py` (fonte) + `.jsonl` (dado). O Colab treina a partir dos jsonl.
