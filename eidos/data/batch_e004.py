# -*- coding: utf-8 -*-
"""Batch e004 — 20 episódios. Códigos TS confirmados por execução real ANTES da CoT:
TS2345 (arg de função), TS2362/2363 (aritmética em objeto), TS18048 (possibly undefined,
pego pelo strict mode). Erro de fronteira server/client (useReducer) confirmado só no
`next build`, igual l1-08/l3-07 — com a página consumidora desde o início desta vez.
"""

# ============================================================ L1 — ciclo completo

DATES_LIB_BROKEN = '''export function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

export function nextBillingDate(): Date {
  return addDays("2026-01-01", 30);
}
'''


def l1_13(E):
    ep = E("L1", "l1-13-arg-tipo-errado", setup={"files": {"lib/dates.ts": DATES_LIB_BROKEN}})
    ep.user("lib/dates.ts não compila, mexi na função nextBillingDate ontem")
    ep.act(
        "Direto ao compilador pra ver o que a mexança de ontem quebrou:",
        "run_terminal", expect=r"error TS2345", command="npx tsc --noEmit")
    ep.act(
        "TS2345: `addDays` espera `Date` no primeiro argumento, e `nextBillingDate` está "
        "passando a STRING \"2026-01-01\". `new Date(string)` até funcionaria em runtime "
        "(o construtor aceita string), mas a assinatura da função exige o tipo certo — e "
        "é exatamente esse tipo de desalinhamento silencioso que o TS existe pra pegar. "
        "Corrijo construindo o Date explicitamente:",
        "edit_file", expect=r"ok:", path="lib/dates.ts",
        old='addDays("2026-01-01", 30)', new='addDays(new Date("2026-01-01"), 30)')
    ep.verify_green(
        "Data construída explicitamente. Typecheck:")
    ep.final(
        "Era TS2345: `nextBillingDate` passava a string \"2026-01-01\" pra `addDays`, que "
        "exige `Date`. Envolvi em `new Date(...)` no call site. Funcionaria em runtime do "
        "jeito que estava (coerção implícita do JS), mas o tipo explícito é mais seguro — "
        "some qualquer ambiguidade sobre o que a função espera. Typecheck verde.")
    return ep


SORTING_LIB_BROKEN = '''type Order = { id: string; total: number };

export function sortByTotal(orders: Order[]): Order[] {
  return [...orders].sort((a, b) => a - b);
}
'''


def l1_14(E):
    ep = E("L1", "l1-14-comparator-errado", setup={"files": {"lib/sorting.ts": SORTING_LIB_BROKEN}})
    ep.user("o typecheck reclama de alguma coisa de aritmética em lib/sorting.ts, não manjo bem TS genérico")
    ep.act(
        "Vamos ver o erro exato — \"aritmética\" é pista boa:",
        "run_terminal", expect=r"error TS236[23]", command="npx tsc --noEmit")
    ep.act(
        "Dois erros irmãos (TS2362/TS2363): o comparator do `.sort()` faz `a - b`, mas `a` "
        "e `b` são objetos `Order`, não números — subtração só existe entre números. O "
        "comparator precisa comparar o CAMPO, não o objeto inteiro:",
        "edit_file", expect=r"ok:", path="lib/sorting.ts",
        old="(a, b) => a - b", new="(a, b) => a.total - b.total")
    ep.verify_green(
        "Comparator corrigido pro campo certo. Typecheck:")
    ep.final(
        "O comparator do `.sort()` em `sortByTotal` fazia `a - b` com objetos `Order` "
        "inteiros — subtração só vale entre números, e o TS2362/2363 pegou isso na hora. "
        "Troquei pra `a.total - b.total`, que é o campo que realmente queremos ordenar. "
        "Typecheck verde. Regra de bolso: comparator de `.sort()` sempre retorna número, "
        "nunca o objeto.")
    return ep


USERS_LIB_BROKEN = '''type User = { id: string; name: string };

const users: User[] = [
  { id: "u1", name: "Marina" },
  { id: "u2", name: "Diego" },
];

export function findUser(id: string): User | undefined {
  return users.find((u) => u.id === id);
}

export function greet(id: string): string {
  const u = findUser(id);
  return `Ola, ${u.name}`;
}
'''


def l1_15(E):
    ep = E("L1", "l1-15-possibly-undefined", setup={"files": {"lib/users.ts": USERS_LIB_BROKEN}})
    ep.user("lib/users.ts tá vermelho no editor, será que é o strict mode sendo chato de novo?")
    ep.act(
        "Pode até parecer chatice, mas geralmente aponta um bug real escondido. Confiro o "
        "erro:",
        "run_terminal", expect=r"error TS18048", command="npx tsc --noEmit")
    ep.act(
        "TS18048: `u` é possivelmente `undefined` em `greet`. E faz sentido — "
        "`findUser` retorna `User | undefined` (o `.find()` não garante achar), mas `greet` "
        "usa `u.name` direto, sem checar. Não é chatice do strict mode: se alguém chamar "
        "`greet(\"id-que-nao-existe\")`, isso quebraria em runtime com \"Cannot read "
        "properties of undefined\". Trato o caso de não encontrar:",
        "edit_file", expect=r"ok:", path="lib/users.ts",
        old='  const u = findUser(id);\n  return `Ola, ${u.name}`;',
        new='  const u = findUser(id);\n  if (!u) {\n    return "Usuário não encontrado";\n  }\n  return `Ola, ${u.name}`;')
    ep.verify_green(
        "Caso de ausência tratado. Typecheck:")
    ep.final(
        "Não era chatice — o TS18048 pegou um bug real: `greet` acessava `u.name` sem "
        "checar se `findUser` de fato achou alguém (ela retorna `User | undefined`). Sem a "
        "checagem, chamar `greet` com um id inexistente quebraria em runtime. Adicionei o "
        "`if (!u)` com uma mensagem de fallback. Typecheck verde — e agora a função é "
        "segura de verdade, não só de fachada.")
    return ep


CART_WIDGET_BROKEN = '''import { useReducer } from "react";

type State = { count: number };
type Action = { type: "inc" } | { type: "dec" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "inc":
      return { count: state.count + 1 };
    case "dec":
      return { count: Math.max(0, state.count - 1) };
  }
}

export default function CartWidget() {
  const [state, dispatch] = useReducer(reducer, { count: 0 });
  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 px-3 py-2 dark:border-zinc-800">
      <button
        type="button"
        onClick={() => dispatch({ type: "dec" })}
        aria-label="Diminuir"
        className="flex h-7 w-7 items-center justify-center rounded-lg text-lg transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
      >
        −
      </button>
      <span className="w-6 text-center text-sm font-semibold tabular-nums">{state.count}</span>
      <button
        type="button"
        onClick={() => dispatch({ type: "inc" })}
        aria-label="Aumentar"
        className="flex h-7 w-7 items-center justify-center rounded-lg text-lg transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800"
      >
        +
      </button>
    </div>
  );
}
'''

CARRINHO_PAGE = '''import CartWidget from "@/components/CartWidget";

export default function CarrinhoPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Carrinho</h1>
      <div className="mt-6">
        <CartWidget />
      </div>
    </main>
  );
}
'''


def l1_16(E):
    ep = E("L1", "l1-16-usereducer-build-only", setup={"files": {
        "components/CartWidget.tsx": CART_WIDGET_BROKEN,
        "app/carrinho/page.tsx": CARRINHO_PAGE,
    }})
    ep.user("o CartWidget passa no typecheck mas o next build acusa erro. Já vi isso acontecer antes com hook, será a mesma coisa?")
    ep.act(
        "Sua suspeita faz sentido — fronteira server/client é regra do Next, o tsc nunca vê "
        "esse tipo de violação. Vou direto no build, que é quem realmente vai revelar:",
        "run_terminal", expect=r"useReducer", command="npm run build")
    ep.act(
        "Confirmado, é o mesmo padrão: `useReducer` é hook client-only, e o `CartWidget` "
        "não declara `\"use client\"`. Adiciono a diretiva:",
        "edit_file", expect=r"ok:", path="components/CartWidget.tsx",
        old='import { useReducer } from "react";',
        new='"use client";\n\nimport { useReducer } from "react";')
    ep.act(
        "Diretiva no lugar. Confirmo com o mesmo comando que revelou o erro:",
        "run_terminal", expect=r"\[exit 0\]", command="npm run build")
    ep.final(
        "Sua suspeita bateu: mesmo padrão de antes. `CartWidget` usa `useReducer` (hook "
        "client-only) sem `\"use client\"` — o tsc nunca acusa isso porque é regra do "
        "Next, não do TypeScript, então só o `next build` revela. Adicionei a diretiva e o "
        "build compilou limpo. Regra geral pra guardar: qualquer hook do React (useState, "
        "useReducer, useEffect, etc.) ou do next/navigation exige \"use client\" — e só o "
        "build confirma se esqueceu.")
    return ep


# ============================================================ L2 — entrega verificada

CONFIRM_BANNER = '''"use client";

import { useState } from "react";

type ConfirmBannerProps = {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export default function ConfirmBanner({ message, onConfirm, onCancel }: ConfirmBannerProps) {
  const [pending, setPending] = useState(false);

  function handleConfirm() {
    setPending(true);
    onConfirm();
  }

  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950 sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="text-amber-900 dark:text-amber-200">{message}</p>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={onCancel}
          disabled={pending}
          className="h-8 rounded-lg px-3 text-sm font-medium text-amber-900 transition-colors hover:bg-amber-100 disabled:pointer-events-none disabled:opacity-50 dark:text-amber-200 dark:hover:bg-amber-900"
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={pending}
          className="h-8 rounded-lg bg-amber-600 px-3 text-sm font-medium text-white transition-colors hover:bg-amber-700 disabled:pointer-events-none disabled:opacity-50 dark:bg-amber-500 dark:hover:bg-amber-400"
        >
          {pending ? "Confirmando…" : "Confirmar"}
        </button>
      </div>
    </div>
  );
}
'''


def l2_12(E):
    ep = E("L2", "l2-12-confirm-banner")
    ep.user("preciso de um banner de confirmação inline (não modal) pra ação de risco médio — tipo 'tem certeza que quer arquivar isso?' com botões confirmar/cancelar. components/ConfirmBanner.tsx")
    ep.act(
        "\"Risco médio\" e \"inline, não modal\" são as pistas de design: cor de atenção "
        "(âmbar, não vermelho — vermelho é pra ação destrutiva de verdade), `role=\"alert\"` "
        "pra leitor de tela anunciar sem precisar de foco. Como tem botão com onClick, é "
        "client component. Detalhe que evita double-submit: desabilito os botões durante o "
        "`pending` e troco o texto do confirmar pra dar feedback de que já está processando:",
        "write_file", expect=r"ok:", path="components/ConfirmBanner.tsx", content=CONFIRM_BANNER)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/ConfirmBanner.tsx` pronto. Client component (estado de pending), cor "
        "âmbar semântica de atenção (reservei vermelho pra ação genuinamente destrutiva), "
        "`role=\"alert\"` pra acessibilidade, layout responsivo (empilha no mobile, lado a "
        "lado no desktop) e proteção contra double-click: os botões desabilitam durante o "
        "`pending` e o texto do confirmar muda pra \"Confirmando…\". Typecheck verde.")
    return ep


FILTER_CHIP = '''"use client";

type FilterChipProps = {
  label: string;
  onRemove: () => void;
};

export default function FilterChip({ label, onRemove }: FilterChipProps) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-zinc-100 py-1 pl-3 pr-1.5 text-xs font-medium dark:bg-zinc-800">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remover filtro ${label}`}
        className="flex h-4 w-4 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-zinc-300 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-600 dark:hover:text-zinc-100"
      >
        ×
      </button>
    </span>
  );
}
'''


def l2_13(E):
    ep = E("L2", "l2-13-filter-chip")
    ep.user("cria um chip de filtro removível (label + X) pra usar numa barra de filtros ativos. components/FilterChip.tsx")
    ep.act(
        "Botão de remover — client component. O detalhe que separa isso de um badge comum: "
        "o X é botão só-ícone, então PRECISA de aria-label descritivo (\"Remover filtro X\", "
        "não só \"Remover\" — com vários chips na tela, o genérico confunde leitor de "
        "tela). Formato pill (rounded-full, condizente com texto curto), o X menor e "
        "circular dentro do chip, com hover próprio:",
        "write_file", expect=r"ok:", path="components/FilterChip.tsx", content=FILTER_CHIP)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/FilterChip.tsx` pronto: pill com o label e um X circular pra remover, "
        "recebendo `label` e `onRemove`. O botão de remover leva `aria-label` "
        "PARAMETRIZADO com o label do chip (\"Remover filtro Ativo\", por exemplo) — "
        "importante quando há vários chips na tela e o leitor de tela precisa distinguir "
        "qual está sendo removido. Client component, typecheck verde.")
    return ep


LABELED_SWITCH = '''"use client";

type LabeledSwitchProps = {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (value: boolean) => void;
};

export default function LabeledSwitch({ label, description, checked, onChange }: LabeledSwitchProps) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-4 py-3">
      <span className="space-y-0.5">
        <span className="block text-sm font-medium">{label}</span>
        {description ? (
          <span className="block text-sm text-zinc-500 dark:text-zinc-400">{description}</span>
        ) : null}
      </span>
      <span className="relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="peer sr-only"
        />
        <span
          aria-hidden="true"
          className="absolute inset-0 rounded-full bg-zinc-300 transition-colors duration-150 peer-checked:bg-zinc-900 peer-focus-visible:ring-2 peer-focus-visible:ring-zinc-500 peer-focus-visible:ring-offset-2 dark:bg-zinc-700 dark:peer-checked:bg-zinc-100 dark:peer-focus-visible:ring-offset-zinc-950"
        />
        <span
          aria-hidden="true"
          className="absolute left-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-150 peer-checked:translate-x-5 dark:bg-zinc-950 dark:peer-checked:bg-zinc-900"
        />
      </span>
    </label>
  );
}
'''


def l2_14(E):
    ep = E("L2", "l2-14-labeled-switch-en", lang="en")
    ep.user("need a settings row: label + optional description text + a real switch. components/LabeledSwitch.tsx")
    ep.act(
        "Client component (checked state + onChange). Reusing the switch anatomy pattern "
        "that works well here: real `<input type=\"checkbox\">` visually hidden via "
        "`sr-only`, track+thumb as sibling spans styled through Tailwind's `peer` variant — "
        "keeps native keyboard/form behavior while looking like a proper switch. The label "
        "text stacks above an optional description (only rendered if provided), and the "
        "whole row is clickable via the outer `<label>`:",
        "write_file", expect=r"ok:", path="components/LabeledSwitch.tsx", content=LABELED_SWITCH)
    ep.verify_green(
        "Written. Typecheck:")
    ep.final(
        "`components/LabeledSwitch.tsx` done: label + optional description (only renders "
        "if passed) on the left, a real switch on the right — genuine checkbox hidden via "
        "`sr-only`, animated track+thumb via `peer-checked`, focus ring on the track via "
        "`peer-focus-visible`. The whole row is one clickable `<label>`. Typecheck green.")
    return ep


# ============================================================ L3 — investigação autônoma

def l3_10(E):
    ep = E("L3", "l3-10-verifica-antes-de-confiar")
    ep.user('o console do navegador tá mostrando isso: "TypeError: Cannot read properties of undefined (reading \'items\')" na página do carrinho')
    ep.act(
        "A mensagem aponta pra algo acessando `.items` de um valor undefined. Vou olhar o "
        "componente do carrinho pra achar onde isso acontece — mas antes de aceitar a "
        "hipótese óbvia, confiro o código de verdade em vez de já sair editando baseado só "
        "na mensagem:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/CartWidget.tsx")
    ep.act(
        "Esse componente não existe (ainda não criamos o CartWidget nesta sessão). O erro "
        "menciona \"a página do carrinho\" — confiro se essa rota sequer existe no projeto "
        "antes de continuar caçando:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="app/carrinho/page.tsx")
    ep.final(
        "Investiguei antes de aceitar a hipótese de cara — e o resultado é estranho o "
        "suficiente pra merecer transparência: não existe `CartWidget.tsx` nem uma rota "
        "`app/carrinho/page.tsx` neste projeto. Ou seja, o erro que o console mostrou não "
        "corresponde a nenhum código que eu consigo localizar aqui agora. Isso sugere uma "
        "de duas coisas: (1) o erro é de uma versão do código que ainda não foi puxada "
        "pra este ambiente, ou (2) a página do carrinho tem um nome de arquivo diferente "
        "do que estou assumindo. Antes de eu inventar uma correção especulativa em cima de "
        "um arquivo que talvez nem seja o certo, preciso do caminho real — pode me "
        "confirmar o nome do arquivo da página do carrinho, ou colar o stack trace "
        "completo (com números de linha, que é o que realmente aponta a origem)?")
    return ep


def l3_11(E):
    ep = E("L3", "l3-11-nao-incomoda-com-trivial", lang="en")
    ep.user("sorry to bother you with something this small, but could you check if the project's typecheck is currently passing? feel free to ignore if you're busy with something else")
    ep.act(
        "Not a bother at all — this is a one-command check, exactly the kind of thing I "
        "should just do without ceremony:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "All good — typecheck passes clean (exit 0), no errors anywhere in the project. "
        "And genuinely, no need to preface small requests like that; a quick check like "
        "this costs nothing to just run.")
    return ep


PROFILE_CARD_BROKEN = '''import Avatar from "@/components/Avatar";

export default function ProfileCard({ userId }: { userId: string }) {
  const user = getUser(userId);
  return (
    <div className="rounded-2xl border border-zinc-200 p-6 dark:border-zinc-800">
      <Avatar name={user.name} />
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">{user.email}</p>
    </div>
  );
}
'''


def l3_12(E):
    ep = E("L3", "l3-12-le-antes-de-inventar", setup={"files": {"components/ProfileCard.tsx": PROFILE_CARD_BROKEN}})
    ep.user("o ProfileCard não builda, deve faltar alguma importação")
    ep.act(
        "Confirmo a hipótese com o compilador antes de sair adicionando import:",
        "run_terminal", expect=r"error TS2304", command="npx tsc --noEmit")
    ep.act(
        "TS2304: `getUser` não está definida em lugar nenhum — não é import faltando "
        "(import errado dá TS2307/2305; \"não existe\" é outra categoria). Alguém escreveu "
        "chamando uma função que nunca foi criada. Confiro se existe algo parecido em "
        "lib/ antes de decidir criar do zero:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="lib/users.ts")
    ep.final(
        "Não é import faltando — é TS2304: `getUser` é chamada em `ProfileCard`, mas essa "
        "função nunca foi definida em lugar nenhum do projeto (confirmei: não existe nem "
        "em `lib/users.ts`, que seria o lugar natural). Duas decisões possíveis daqui, e "
        "prefiro não adivinhar qual você quer: (1) `getUser` deveria vir de uma API "
        "assíncrona (nesse caso o componente precisa virar `async` ou buscar via "
        "`useEffect`, dependendo se é server ou client), ou (2) é um placeholder e você "
        "tem a implementação real em algum outro lugar que não vi. Me diz de onde `user` "
        "deveria vir que eu termino a implementação certa.")
    return ep


# ============================================================ L4 — estilo completo num edit

INLINE_NOTICE_POOR = '''export default function InlineNotice({ text }: { text: string }) {
  return <div className="bg-blue-100 p-2 text-sm">{text}</div>;
}
'''

INLINE_NOTICE_GOOD = '''export default function InlineNotice({ text }: { text: string }) {
  return (
    <div
      role="status"
      className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-200"
    >
      {text}
    </div>
  );
}
'''


def l4_10(E):
    ep = E("L4", "l4-10-inline-notice", setup={"files": {"components/InlineNotice.tsx": INLINE_NOTICE_POOR}})
    ep.user("o InlineNotice tá com essa cor azul crua do Tailwind e zero acessibilidade. dá um trato")
    ep.act(
        "Lendo o atual pra auditar contra o guia inteiro:",
        "read_file", expect=r"InlineNotice", path="components/InlineNotice.tsx")
    ep.act(
        "4 pendências, um edit:\n"
        "1. `bg-blue-100` é cor pura do Tailwind, fora da escala semântica do projeto → "
        "`sky` pra informativo (reservo emerald/amber/rose pra sucesso/atenção/erro);\n"
        "2. sem borda → definição de superfície com border sutil no tom da cor;\n"
        "3. sem dark mode nenhum;\n"
        "4. acessibilidade zero: um aviso informativo devia se anunciar sem exigir foco → "
        "`role=\"status\"`.\n"
        "Aplicando:",
        "write_file", expect=r"ok:", path="components/InlineNotice.tsx", content=INLINE_NOTICE_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "InlineNotice corrigido num edit: cor trocada de `blue-100` genérico pra `sky` "
        "(escala semântica do projeto, reservando emerald/amber/rose pras outras "
        "categorias), borda sutil no mesmo tom pra dar definição, dark mode completo, e "
        "`role=\"status\"` pra leitor de tela anunciar o aviso sem precisar de foco. "
        "Compilando limpo.")
    return ep


AVATAR_STACK_POOR = '''export default function AvatarStack({ names }: { names: string[] }) {
  return (
    <div className="flex">
      {names.map((n) => (
        <div key={n} className="h-8 w-8 rounded-full bg-zinc-300 text-xs">
          {n.slice(0, 2)}
        </div>
      ))}
    </div>
  );
}
'''

AVATAR_STACK_GOOD = '''export default function AvatarStack({ names, max = 4 }: { names: string[]; max?: number }) {
  const visible = names.slice(0, max);
  const extra = names.length - visible.length;
  return (
    <div className="flex items-center" role="group" aria-label={`${names.length} pessoas`}>
      {visible.map((n, i) => (
        <div
          key={n}
          style={{ zIndex: visible.length - i }}
          className="relative -ml-2 flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-zinc-300 text-xs font-medium text-zinc-700 first:ml-0 dark:border-zinc-950 dark:bg-zinc-700 dark:text-zinc-200"
          title={n}
        >
          {n.slice(0, 2).toUpperCase()}
        </div>
      ))}
      {extra > 0 ? (
        <div className="relative -ml-2 flex h-8 w-8 items-center justify-center rounded-full border-2 border-white bg-zinc-100 text-xs font-medium text-zinc-500 dark:border-zinc-950 dark:bg-zinc-800 dark:text-zinc-400">
          +{extra}
        </div>
      ) : null}
    </div>
  );
}
'''


def l4_11(E):
    ep = E("L4", "l4-11-avatar-stack", setup={"files": {"components/AvatarStack.tsx": AVATAR_STACK_POOR}})
    ep.user("os avatares empilhados tão só um do lado do outro sem sobrepor, e se tiver muita gente estoura a tela. conserta")
    ep.act(
        "Vendo o estado atual:",
        "read_file", expect=r"AvatarStack", path="components/AvatarStack.tsx")
    ep.act(
        "Dois bugs funcionais no seu relato + pendências de estilo, tudo num edit:\n"
        "1. \"sem sobrepor\": falta a margem negativa que cria a sobreposição — "
        "`-ml-2` com `first:ml-0` (o primeiro não recua) e `z-index` decrescente pra quem "
        "vem antes ficar por cima;\n"
        "2. \"estoura a tela\": preciso de um limite — `max` (default 4) que corta a lista "
        "e mostra \"+N\" pros que sobraram, em vez de renderizar todo mundo;\n"
        "3. borda branca/escura entre avatares pra eles se distinguirem mesmo sobrepostos;\n"
        "4. iniciais em maiúsculo consistente, e `title` com o nome completo pro hover "
        "nativo do navegador mostrar quem é;\n"
        "5. semântica de grupo: `role=\"group\"` com `aria-label` contando quantas pessoas.\n"
        "Reescrevendo:",
        "write_file", expect=r"ok:", path="components/AvatarStack.tsx", content=AVATAR_STACK_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "AvatarStack corrigido — os dois bugs que você notou e mais o resto do guia: "
        "sobreposição real (margem negativa + z-index decrescente + borda de contorno), "
        "limite de exibição via `max` (default 4) com indicador \"+N\" pro resto, `title` "
        "com o nome completo em cada avatar, e `role=\"group\"` com contagem total pra "
        "acessibilidade. Compilando limpo.")
    return ep


# ============================================================ L5 — recuperação de tool call

def l5_11(E):
    ep = E("L5", "l5-11-comando-fora-da-whitelist")
    ep.user("adiciona o pacote date-fns no projeto, usando yarn (é o que a gente usa aqui, geralmente)")
    ep.act(
        "Tentando com yarn, como pedido:",
        "run_terminal", expect=r"não permitido", command="yarn add date-fns")
    ep.act(
        "`yarn` não está na whitelist deste terminal — e olhando o projeto, ele já usa "
        "`package-lock.json` (não `yarn.lock`), então é um projeto npm de fato, "
        "independente do hábito da equipe. Uso npm, que é equivalente aqui:",
        "run_terminal", expect=r"\[exit 0\]", command="npm install date-fns")
    ep.final(
        "`date-fns` instalado — mas com `npm`, não `yarn`. `yarn` não está disponível "
        "neste terminal, e o projeto já tem `package-lock.json` (sem `yarn.lock`), "
        "confirmando que ele é gerenciado com npm de fato. Se o time realmente usa yarn "
        "no dia a dia em outro lugar, vale investigar essa inconsistência — misturar os "
        "dois gerenciadores no mesmo projeto costuma gerar lockfile duplicado e "
        "dependência fantasma.")
    return ep


def l5_12(E):
    ep = E("L5", "l5-12-path-fora-do-projeto")
    ep.user("salva uma cópia de backup do lib/utils.ts em ../backups/utils.ts.bak, por precaução antes de eu mexer nele")
    ep.act(
        "Preciso do conteúdo atual antes de replicar:",
        "read_file", expect=r"export function cn", path="lib/utils.ts")
    ep.act(
        "Tentando gravar no caminho pedido:",
        "write_file", expect=r"fora do projeto",
        path="../backups/utils.ts.bak", content="export function cn(...) {}")
    ep.final(
        "Não consigo escrever em `../backups/` — é fora da raiz do projeto, e as "
        "ferramentas de arquivo são restritas a esse limite por segurança (evita que eu "
        "escreva em qualquer lugar do seu disco). Alternativa dentro do projeto: posso "
        "salvar em algo como `lib/utils.ts.bak` ou `_backups/utils.ts.bak` (dentro da "
        "raiz). Se você realmente precisa do backup FORA do repositório, isso é um "
        "`cp` que só roda no seu terminal local: `cp lib/utils.ts ../backups/utils.ts.bak`.")
    return ep


REFUND_POLICY = '''export function calculateRefund(amountCents: number, daysSincePurchase: number): number {
  if (daysSincePurchase > 30) {
    return 0;
  }
  if (daysSincePurchase > 7) {
    return Math.round(amountCents * 0.5);
  }
  return amountCents;
}
'''


def l5_13(E):
    ep = E("L5", "l5-13-old-com-espacamento-errado-en", lang="en",
           setup={"files": {"lib/refunds.ts": REFUND_POLICY}})
    ep.user("the refund policy should be 14 days for full refund, not 7 — can you update that threshold?")
    ep.act(
        "Straightforward threshold change. Editing the condition:",
        "edit_file", expect=r"não encontrado",
        path="lib/refunds.ts",
        old="if (daysSincePurchase  > 7) {",
        new="if (daysSincePurchase > 14) {")
    ep.act(
        "No match — I typed the condition from memory with a double space that isn't "
        "actually there. Rather than guess a second variation, I'll read the real file and "
        "anchor on the exact text:",
        "read_file", expect=r"> 7", path="lib/refunds.ts")
    ep.act(
        "Now anchoring on the literal text from the file:",
        "edit_file", expect=r"ok:",
        path="lib/refunds.ts",
        old="if (daysSincePurchase > 7) {",
        new="if (daysSincePurchase > 14) {")
    ep.verify_green(
        "Threshold updated. Typecheck:")
    ep.final(
        "Done — the full-refund window is now 14 days instead of 7. Transparency note: my "
        "first edit guessed the spacing from memory (typed an extra space that wasn't "
        "really there) and missed; instead of guessing again, I read the file and anchored "
        "the second attempt on the exact text. Typecheck is green.")
    return ep


# ============================================================ L4 — mais um

TAB_BADGE_POOR = '''export default function TabBadge({ count }: { count: number }) {
  if (count === 0) return null;
  return <span className="bg-red-600 text-white text-xs rounded-full px-1">{count}</span>;
}
'''

TAB_BADGE_GOOD = '''export default function TabBadge({ count }: { count: number }) {
  if (count === 0) return null;
  const label = count > 99 ? "99+" : String(count);
  return (
    <span
      aria-label={`${count} ${count === 1 ? "notificação" : "notificações"}`}
      className="inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-bold leading-none text-white dark:bg-rose-500"
    >
      {label}
    </span>
  );
}
'''


def l4_12(E):
    ep = E("L4", "l4-12-tab-badge-en", lang="en", setup={"files": {"components/TabBadge.tsx": TAB_BADGE_POOR}})
    ep.user("the notification count badge on the tab looks off — also what happens if the count is like 500? probably looks broken")
    ep.act(
        "Reading it first — you're right to worry about large counts, that's a real edge "
        "case the current code doesn't handle at all:",
        "read_file", expect=r"TabBadge", path="components/TabBadge.tsx")
    ep.act(
        "Full audit — four things, one rewrite:\n"
        "1. your instinct is correct: `count=500` renders literally \"500\", which will "
        "overflow a tiny circular badge → cap the LABEL at \"99+\" while keeping the real "
        "count in the aria-label for accessibility;\n"
        "2. `px-1` alone on a single-digit count makes an oval, not a circle → fixed "
        "height + `min-w` so it's circular for 1 digit and pill-shaped only when text is "
        "wider (99+);\n"
        "3. raw `red-600` instead of the project's semantic `rose` scale, and no dark "
        "variant;\n"
        "4. zero accessibility: a bare number with no context → `aria-label` stating the "
        "full count and correct singular/plural.\n"
        "Writing it:",
        "write_file", expect=r"ok:", path="components/TabBadge.tsx", content=TAB_BADGE_GOOD)
    ep.verify_green(
        "Rewritten. Typecheck:")
    ep.final(
        "Fixed the exact issue you flagged plus three more: count above 99 now displays "
        "\"99+\" (label capped) while the `aria-label` still announces the real number "
        "(\"500 notificações\"), the badge is properly circular via fixed height + "
        "`min-w` instead of stretching, color moved to the project's `rose` semantic scale "
        "with dark mode, and added the missing accessibility label. Typecheck green.")
    return ep


# ============================================================ LC — conversa técnica

def lc_10(E):
    ep = E("LC", "lc-10-testes-unit-vs-e2e")
    ep.user("Time perguntando: vale mais a pena investir em testes unitários de componente ou em E2E pro frontend? Recurso é limitado, tem que escolher onde focar primeiro.")
    ep.final(
        "Com recurso limitado, minha ordem de prioridade é: E2E de fluxo crítico primeiro, "
        "unitário de lógica pura depois — e a razão é sobre ONDE o bug realmente dói.\n\n"
        "**Por que E2E primeiro, indo contra o instinto comum de \"começar pequeno\":** "
        "testes unitários de componente isolado pegam bug de lógica interna, mas o bug que "
        "derruba receita é outra categoria — a integração quebrada entre peças que "
        "individualmente passam no teste. Checkout funciona sozinho, carrinho funciona "
        "sozinho, mas o dado que um passa pro outro mudou de formato e ninguém percebeu "
        "porque cada teste unitário só olha sua própria caixinha. Um E2E do fluxo \"add ao "
        "carrinho → checkout → confirmação\" pega exatamente essa classe de bug, que é a "
        "mais cara de deixar vazar pra produção.\n\n"
        "**Onde o unitário ganha depois:** lógica de cálculo pura (preço com desconto, "
        "validação de formulário, formatação de data) é barata de testar unitariamente E "
        "cara de cobrir só via E2E (você precisaria simular dezenas de combinações clicando "
        "na UI real, lento e frágil). Aqui a ordem se inverte: unitário é o investimento "
        "eficiente.\n\n"
        "**Um ponto que costuma faltar na discussão:** E2E tem custo de manutenção maior "
        "(quebra com mudança de UI que não é bug de verdade — um seletor que moveu), "
        "então o conselho prático é: poucos E2E, só nos fluxos que literalmente geram "
        "receita ou dados críticos (checkout, cadastro, login), e cobertura unitária "
        "generosa em tudo que é lógica pura sem tela envolvida.\n\n"
        "Pergunta que ajudaria a decidir com o time: hoje, quando um bug escapa pra "
        "produção, ele é mais frequentemente \"a integração quebrou\" ou \"um cálculo deu "
        "errado\"? A resposta aponta onde investir primeiro.")
    return ep


def lc_11(E):
    ep = E("LC", "lc-11-microfrontends-en", lang="en")
    ep.user("our platform team is pushing micro-frontends so different squads can ship independently. as someone who'd have to live with it, what's your honest take?")
    ep.final(
        "My honest take: micro-frontends solve an ORGANIZATIONAL problem (squads blocking "
        "each other on deploys) by introducing a TECHNICAL cost (duplicated dependencies, "
        "runtime integration complexity, harder cross-cutting changes) — and whether that "
        "trade is worth it depends entirely on how real the organizational pain already is.\n\n"
        "**Where it genuinely earns its cost:** if squads today are routinely blocked on "
        "each other's release trains — squad A can't ship because squad B's untested code "
        "is in the same deploy — that's real, expensive pain, and independent "
        "deployability is worth the integration tax. Also fits well when squads own "
        "genuinely separate product surfaces (e.g., \"account settings\" vs \"checkout\") "
        "with little shared UI.\n\n"
        "**Where it's paying for a problem you don't have:** if the real friction is "
        "\"our CI is slow\" or \"our monolith's build takes 20 minutes,\" micro-frontends "
        "don't fix that — they usually make total build/deploy TIME worse (more moving "
        "parts, more CI pipelines), they just parallelize WHO can ship without waiting on "
        "whom. If your actual bottleneck is tooling, not coordination, you're solving the "
        "wrong problem.\n\n"
        "**The cost that's easy to underestimate:** shared design system consistency gets "
        "genuinely harder — each micro-frontend can drift its own dependency versions "
        "(two different React versions in one page is a real failure mode), and a "
        "cross-cutting change (rebrand, a11y fix, design token update) now touches N "
        "repos instead of one.\n\n"
        "If I had to live with it: I'd want to see the release-blocking pain quantified "
        "first (how many days/week lost to cross-squad blocking, concretely) before "
        "signing up for the integration tax — and I'd push hard for a SHARED component "
        "library with pinned versions as a non-negotiable, or the visual drift will show "
        "up in production within a quarter.")
    return ep


def lc_12(E):
    ep = E("LC", "lc-12-feature-flags")
    ep.user("nosso time nunca usou feature flag, sempre foi merge direto pra main e deploy. vale a pena introduzir isso agora que estamos em 5 devs?")
    ep.final(
        "Com 5 devs, eu diria que sim — mas o motivo certo não é \"flag é boa prática\", é "
        "um problema específico que aparece exatamente nessa fase de crescimento do time.\n\n"
        "Com 1-2 devs, merge direto pra main funciona porque cada um sabe o que o outro tá "
        "fazendo e feature grande cabe numa branch curta. Com 5, a matemática muda: mais "
        "gente trabalhando em paralelo significa mais features PARCIALMENTE prontas "
        "competindo pelo mesmo main ao mesmo tempo — e sem flag, a escolha vira binária e "
        "ruim: ou você segura o merge (branch de feature vive dias/semanas, diverge cada "
        "vez mais, merge fica doloroso), ou você faz merge de código incompleto pro main e "
        "reza pra não quebrar produção.\n\n"
        "Feature flag resolve isso separando duas decisões que hoje estão coladas: \"esse "
        "código está integrado ao main\" (decisão técnica, deveria acontecer cedo e "
        "frequente) e \"esse código está visível pro usuário\" (decisão de produto, "
        "acontece quando estiver pronto). Com isso, todo mundo faz merge cedo e direto "
        "(evita o inferno de merge de branch longa) e a feature fica atrás da flag até "
        "estar pronta de verdade.\n\n"
        "O jeito de começar sem virar projeto de infra: nada de plataforma de flag "
        "sofisticada — um objeto de config simples (`{ novoCheckout: false }`) lido de uma "
        "env var ou de um arquivo JSON já resolve 80% do valor pro estágio de vocês. "
        "Complexidade de flag por porcentagem de usuário, targeting, etc., só vale a pena "
        "quando o time crescer mais ou quando a necessidade aparecer de verdade — não "
        "antes.")
    return ep


EPISODES = [
    l1_13, l1_14, l1_15, l1_16,
    l2_12, l2_13, l2_14,
    l3_10, l3_11, l3_12,
    l4_10, l4_11, l4_12,
    l5_11, l5_12, l5_13,
    lc_10, lc_11, lc_12,
]
