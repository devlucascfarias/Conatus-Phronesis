# Progresso do dataset Eidos — Fase 1/2

- **Meta (decisão do sócio, 2026-07-22): 50 exemplos POR CAMADA × 6 = 300 episódios**,
  com CoT técnico desenvolvido (substituiu o piloto de ~20 do plano original).
- Spec: `prompts/generator_eidos.md`. Builder: `build_episodes.py` (execução real,
  outputs autênticos, QA por `expect`).
- Fonte = `batch_eNNN.py` (código); dado = `episodes_eNNN.jsonl` (commitados juntos).
- Regra de ouro: NENHUM arquivo/bug/prompt do `eval_cases.jsonl` reusado (testset).

## Estado

| Camada | Meta | Feito | Batches |
|---|---|---|---|
| L1 ciclo completo | 50 | 8 | e001, e002 |
| L2 entrega verificada | 50 | 7 | e001, e002 |
| L3 investigação autônoma | 50 | 6 | e001, e002 |
| L4 estilo completo | 50 | 6 | e001, e002 |
| L5 recuperação de tool | 50 | 6 | e001, e002 |
| LC conversa técnica | 50 | 7 | e001, e002 |
| **Total** | **300** | **40** | |

## Batches

### e001 (20 ep) — o lote de ouro
Fixa o padrão de cada camada. L1: import quebrado em merge, TS2366 de retorno faltante,
JSX não fechado, typo de método (en). L2: OrderSummary, RatingStars (a11y de SVG),
QuantityPicker (client). L3: recusa colar código ("eu leio direto"), dependência fantasma,
recusa screenshot (en). L4: auditoria completa em edit único — PromoTile (7 pendências),
SubscribeBox (6, com a11y de label), StatChip (en). L5: chave errada file_path→path,
edit ambíguo (old aparece 2x), comando rm bloqueado→npm install. LC: Tailwind vs Modules,
Zustand vs Context, "use client em tudo" (pushback respeitoso), dark mode em tool interno (en).

### e002 (20 ep)
L1: módulo ausente criado do zero, erro EM CASCATA (2 tsc seguidos, resolve um por vez),
const perdida em extração de código, "use client" que só o `next build` pega (tsc engana).
L2: InvoiceList (Record tipado por status), CopyField (clipboard client), StatusPage
(reusa Card/Button do projeto), KbdHint (en, elemento semântico `<kbd>`). L3: roda tsc e
reporta sem mexer em nada, acha o arquivo certo por tentativa de nome (LoginForm→
LoginPanel), reproduz erro de CI localmente em vez de pedir os logs (en). L4: indicador de
etapa textual→visual com a11y, seletor de planos com bug funcional (prop ignorada) +
estilo, usage meter com tons por threshold (en). L5: path errado corrigido por tentativa
(HeaderNav→Navbar), edit que falha e REANCORA relendo o arquivo (não chuta 2x), curl
bloqueado→`npm view` como alternativa permitida (en). LC: fontes custom e Lighthouse
(FOIT/FOUT + CLS), como explicar RSC pra júnior (3 atos), tabs vs accordion mobile (en).

### Bug corrigido durante e002
`l1-08` (use-client só quebra no build) inicialmente não quebrava: o arquivo
`LikeButton.tsx` plantado não era importado por nenhuma página, então o Next nem tentava
compilá-lo (arquivo órfão fora da árvore de build). Corrigido plantando também uma página
que importa e usa o componente — só aí o erro de fronteira server/client se manifesta.
Lição: setup de cenário precisa considerar a ÁRVORE DE IMPORTS do Next, não só o arquivo.

## Lições de construção (evitar retrabalho)

- Todo bug plantado precisa de `expect` no primeiro tsc (QA: quebra como prometido).
- Camadas de código fecham com `verify_green()` — sem exceção.
- Arquivos plantados novos são typecheckados junto: só podem importar o que existe no template.
- `ls` NÃO funciona no builder local (Windows/cmd) — localizar arquivo pelo erro do tsc,
  que é o padrão que queremos ensinar de qualquer forma.
- Variar: código de erro TS, registro do usuário, nº de ações (2-6), ~15% en.
- **Erro de fronteira Next (server/client) só se manifesta se o arquivo estiver na árvore
  de imports de alguma página.** Sempre plantar (ou apontar pra) o arquivo consumidor junto.
- `validate_args`: `new` (edit_file, apagar trecho) e `content` (write_file, arquivo vazio)
  são strings vazias LEGÍTIMAS — só `path`/`old`/`command` não podem ser vazios.
