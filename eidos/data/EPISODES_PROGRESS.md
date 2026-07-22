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
| L1 ciclo completo | 50 | 20 | e001-e005 |
| L2 entrega verificada | 50 | 17 | e001-e005 |
| L3 investigação autônoma | 50 | 15 | e001-e005 |
| L4 estilo completo | 50 | 15 | e001-e005 |
| L5 recuperação de tool | 50 | 16 | e001-e005 |
| LC conversa técnica | 50 | 15 | e001-e005 |
| **Total** | **300** | **98** | |

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

### e003 (20 ep) — 3 bugs pegos ANTES de escrever a CoT (probe isolado)
Testei os bugs de L1 num script isolado contra o template real ANTES de escrever a CoT,
pra citar o código TS verdadeiro em vez de chutar. Descartei um cenário de "export default
ausente" (TS2613) porque a mensagem do TypeScript pra esse erro embute o CAMINHO ABSOLUTO
do disco — vazaria path de máquina de dev pro dataset; troquei por prop obrigatória
ausente (TS2741), que sai limpo. Códigos confirmados por execução real: TS2322 (tipo
incompatível: string numa prop number), TS2551 (typo de propriedade, .lenght), TS2741
(prop obrigatória faltando — resolvido com placeholder honesto, não valor inventado),
TS1005 (vírgula faltando, erro em cascata). L2: ToastNotification (auto-dismiss client),
SearchEmptyState, FieldHint (tooltip só CSS com group-hover E focus-within, cobre teclado),
ActivityItem (en, elemento semântico `<time>`). L3: repete o padrão "não precisa mandar
nada" com bug NOVO (use-client em usePathnamepau — igual ao l1-08, só detectável no
build), conserta em vez de só apontar quando pedem só o nome do arquivo (en, com
julgamento sobre limite do pedido), escopo honesto (investiga o front, não acha bug, relata
suspeita do back sem fingir certeza). L4: DiscountTag (cor genérica→semântica), DataRow
(layout empilhado→flex), ToggleRow (checkbox→switch visual mantendo input real, en). L5:
nome de tool errado (save_file→write_file), tipo errado no argumento (new como número),
comando git bloqueado (fora da whitelist, sem alternativa — explica a limitação), edit
reancorado por suposição de formatação errada (en). LC: monorepo vs multi-repo (critério =
nº de repos compartilhando código, não tamanho do time), TypeScript strict mode em código
legado (estratégia incremental, en).

### Bugs corrigidos durante e003
1. `l3-07` original usava `tsc` pra pegar erro de "use client" ausente — mas essa classe de
   erro (fronteira server/client) só o `next build` detecta, o mesmo padrão do `l1-08`.
   Corrigido: build em vez de tsc, e adicionada a página consumidora (mesma lição do e002).
2. `l5-10` simulava um primeiro edit "errado" por suposição de formatação, mas o texto que
   escrevi por engano CASOU com o arquivo real (sucesso na primeira tentativa, não o que o
   cenário queria ensinar). Corrigido: a suposição errada agora assume JSX multi-linha
   quando o arquivo real é inline — diverge de verdade, testado isolado antes de rodar o
   batch inteiro.

### Correção retroativa: vazamento de ANSI + path absoluto (achada entre e003 e e004)
Antes de escrever e004, testei um novo bug de fronteira server/client (useReducer) e
descobri que a saída REAL do `next build` embute códigos ANSI de cor crus (`\x1b[31m` etc)
E o caminho ABSOLUTO da máquina de dev no code-frame do erro. Isso já tinha vazado, sem eu
perceber, pros episódios `l1-08` (e002) e `l3-07` (e003) — os únicos 2 que usam build
error antes desta correção. Fix na raiz: `exec_run_terminal` (compartilhado entre o eval
harness e o builder de episódios) agora sanitiza ANSI e normaliza o path absoluto do
workdir pra relativo em TODA saída de terminal. e002 e e003 foram reconstruídos com saída
limpa; varredura no dataset inteiro (79 episódios) confirma zero vazamentos.

### e004 (19 ep) — 2 bugs de cenário pegos pela execução real (mesmo após probe prévio)
Novos códigos TS confirmados por execução antes da CoT: TS2345 (arg de função com tipo
errado), TS2362/2363 (aritmética em objeto no lugar de campo — comparator de `.sort()`),
TS18048 (possibly undefined, pego pelo strict mode — resolvido com fallback explícito, não
com `!` de asserção). L1 também repete "use client só quebra no build" com useReducer,
desta vez com a página consumidora plantada desde a primeira tentativa. L2: ConfirmBanner
(inline, não modal, com proteção contra double-submit), FilterChip (aria-label
parametrizado com o nome do filtro), LabeledSwitch (en). L3: verifica a mensagem do
console ANTES de agir (não acha o arquivo, admite limitação em vez de inventar correção
especulativa), não exige formalidade pra pedido trivial (en), lê o código antes de assumir
"deve ser import faltando" (era TS2304 de função nunca definida, não import). L4:
InlineNotice (cor genérica→semântica + role=status), AvatarStack (dois bugs funcionais
relatados pelo usuário + estilo: sobreposição ausente e sem limite de exibição), TabBadge
(cap "99+" mantendo contagem real no aria-label, en). L5: yarn bloqueado→npm (mais
detecção de que o projeto já usa package-lock, não yarn.lock), write fora da raiz do
projeto bloqueado por segurança (sem workaround — é limite de fato), edit reancorado por
espaçamento errado assumido de memória (en). LC: testes unitário vs E2E (prioridade por
onde o bug realmente dói, não por tamanho do teste), micro-frontends (problema
organizacional vs custo técnico, en), feature flags num time de 5 (separa "integrado" de
"visível pro usuário").

Bugs de cenário corrigidos ANTES do commit (nenhum chegou a ser commitado quebrado):
1. `l5-13` original assumia que o primeiro edit falharia, mas o texto coincidia com o
   arquivo real (sucesso na primeira tentativa) — e o episódio ficava incompleto, sem
   `verify_green`/`final`. Reescrito do zero com uma divergência real (espaço duplo
   assumido) testada isolada antes de rodar o batch.
2. `l3-10` assumia que a home do template mencionaria "carrinho" — não faz sentido, a home
   é sobre o próprio harness Eidos, não um e-commerce. Corrigido pra checar
   `app/carrinho/page.tsx` (que também não existe no cenário, e essa ausência É a resposta
   correta — o modelo relata limite honesto em vez de inventar).
3. Armadilha de ferramenta: `python script.py 2>&1 | tail -N` **mascara o exit code real**
   do script (o exit code do pipeline vira o do `tail`, que é sempre 0). Um crash real
   passou despercebido por isso. Sempre redirecionar pra arquivo (`> log 2>&1; echo $?`)
   em vez de pipe pra tail quando o exit code importa pra QA.

### e005 (19 ep) — primeiro batch sem NENHUM bug de cenário (probe prévio + disciplina pagando)
Códigos TS confirmados por execução antes da CoT: TS2588 (reatribuição de const → `let`),
TS2365 (await faltando: Promise usada em aritmética), TS2323/2393 (identificador
duplicado, merge). L1 também ganhou um caso sem NENHUM erro de tipo: `l1-20` é bug de
LÓGICA (desconto tratado como 1000% em vez de 10% por esquecer de dividir por 100) — o
tsc passa limpo, e o modelo precisa ler o código em vez de rodar o compilador de novo,
reforçando que "ciclo completo" não é só sobre erros de tipo. L2: BackToTopButton (scroll
listener passive + cleanup), ReadingTime (contagem de palavras robusta a espaços
múltiplos), ExpandableText (en, botão só aparece se precisa truncar). L3: verifica e
REFUTA a hipótese de bug do próprio usuário em vez de aplicar a correção baseada nela
cegamente, reproduz "funciona na minha máquina" e aponta lockfile como suspeito nº 1 (en),
lê o código antes de assumir arquitetura nova pra uma feature (carrinho mockado). L4:
RatingSummary (bug de plural relatado pelo usuário confirmado + estilo), TimestampBadge
(ISO crua → tempo relativo, mas a data completa preservada no `title`), SocialLinks (en,
bug de segurança que vem de brinde: `target="_blank"` sem `rel="noopener noreferrer"`).
L5: path aninhado errado (assume `components/ui/`, corrige pro flat), extensão errada
(assume `.jsx`, projeto é `.tsx`), `content` como lista em vez de string (en). LC: REST vs
GraphQL (critério = overfetching/underfetching crônico, não moda), BEM na era Tailwind (o
problema original sumiu, mas sobrevive em miniatura pra classes customizadas extraídas,
en), kit de UI pra MVP (shadcn-like > biblioteca fechada, pela saída de emergência depois).

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
- **Testar bug novo ISOLADO antes de escrever a CoT** (probe rápido via `reset_workdir`+
  `apply_setup`+`tsc`): mais barato que escrever a narrativa inteira e só descobrir depois
  que o código TS citado está errado ou que o erro nem se manifesta.
- Erros de RESOLUÇÃO DE MÓDULO (import/export ausente, ex. TS2613) podem embutir caminho
  ABSOLUTO do disco na mensagem — não usar esses cenários sem checar primeiro; preferir
  TS2741 (prop obrigatória) ou similares que citam só `arquivo(linha,coluna)` relativo.
- O code-frame de erro do `next build` (fronteira server/client) embute ANSI + path
  absoluto — já sanitizado na raiz (`exec_run_terminal`), mas vale lembrar ao ler outputs
  crus de terminal fora desse executor.
- `python x.py 2>&1 | tail -N` mascara o exit code real (vira o do `tail`). Pra QA que
  depende do exit code, redirecionar pra arquivo e checar `$?` separadamente.
- Bug funcional relatado pelo usuário (ex.: "prop ignorada", "sem sobrepor") deve ser
  corrigido ANTES de aplicar o polimento visual — e a CoT deve nomear o bug funcional
  primeiro, separado da lista de pendências estéticas.
