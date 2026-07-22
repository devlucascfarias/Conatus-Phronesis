# -*- coding: utf-8 -*-
"""Batch e006 — 19 episódios. Códigos/comportamentos confirmados por execução real ANTES
da CoT: TS2322 cascata via useState([]) sem generic (inferência 'never[]' — um dos bugs
mais comuns de React+TS de verdade), TS2740 (Set no lugar de array), TS2322 de union type
sem o literal novo, npm install com typo real (E404) corrigido pro nome certo.
"""

# ============================================================ L1 — ciclo completo

WISHLIST_BROKEN = '''"use client";

import { useState } from "react";

export default function WishlistWidget() {
  const [items, setItems] = useState([]);

  function addItem(name: string) {
    setItems([...items, { name, addedAt: Date.now() }]);
  }

  return (
    <ul className="space-y-1">
      {items.map((item) => (
        <li key={item.name} className="text-sm">{item.name}</li>
      ))}
    </ul>
  );
}
'''

WISHLIST_FIXED_TYPE = "type WishlistItem = { name: string; addedAt: number };\n\n"


def l1_21(E):
    ep = E("L1", "l1-21-usestate-sem-generic", setup={"files": {"components/WishlistWidget.tsx": WISHLIST_BROKEN}})
    ep.user("o WishlistWidget tá dando um monte de erro de tipo, mas eu só chamei useState normal")
    ep.act(
        "\"useState normal\" às vezes esconde o problema mais comum dessa dupla React+TS — "
        "confiro os erros exatos:",
        "run_terminal", expect=r"error TS2322", command="npx tsc --noEmit")
    ep.act(
        "Vários TS2322/TS2339 em cascata, todos girando em torno de tipo `never`. É o "
        "clássico: `useState([])` sem generic explícito faz o TypeScript inferir o tipo "
        "do array a partir do valor inicial — um array vazio infere `never[]`, porque não "
        "há elemento nenhum pra inferir o tipo de. Todo `setItems([...items, {...}])` "
        "depois vira erro, porque nada é atribuível a `never`. Confirmo lendo o arquivo "
        "antes de decidir o tipo certo do item:",
        "read_file", expect=r"addedAt", path="components/WishlistWidget.tsx")
    ep.act(
        "O item tem `name: string` e `addedAt: number` — dou um tipo explícito ao "
        "`useState` em vez de deixar o TS adivinhar a partir do array vazio:",
        "edit_file", expect=r"ok:", path="components/WishlistWidget.tsx",
        old='import { useState } from "react";\n\nexport default function WishlistWidget() {\n  const [items, setItems] = useState([]);',
        new=('import { useState } from "react";\n\n' + WISHLIST_FIXED_TYPE
             + 'export default function WishlistWidget() {\n  const [items, setItems] = useState<WishlistItem[]>([]);'))
    ep.verify_green(
        "Generic explícito adicionado. Typecheck:")
    ep.final(
        "Era o bug mais clássico de React+TypeScript: `useState([])` sem generic explícito "
        "infere `never[]` a partir do array vazio inicial — e qualquer `setItems` depois "
        "vira erro de tipo, em cascata. Corrigi com `useState<WishlistItem[]>([])`, dando "
        "o tipo explicitamente em vez de deixar o TS adivinhar do valor inicial vazio. "
        "Regra de bolso: sempre que `useState` começa com array ou objeto vazio "
        "(`[]`/`{}`/`null`), o generic explícito evita essa classe inteira de erro.")
    return ep


TAGS_LIB_BROKEN = '''export function parseTags(raw: string): string[] {
  return raw.split(",").map((t) => t.trim());
}

export function uniqueTags(raw: string): string[] {
  const tags = parseTags(raw);
  return new Set(tags);
}
'''


def l1_22(E):
    ep = E("L1", "l1-22-set-no-lugar-de-array", setup={"files": {"lib/tags.ts": TAGS_LIB_BROKEN}})
    ep.user("lib/tags.ts não compila, usei Set pra remover duplicata mas deu erro")
    ep.act(
        "Confiro o erro exato — `Set` remover duplicata está certo conceitualmente, o "
        "problema deve ser de conversão:",
        "run_terminal", expect=r"error TS2740", command="npx tsc --noEmit")
    ep.act(
        "TS2740: `uniqueTags` promete devolver `string[]`, mas devolve um `Set<string>` "
        "puro — faltou converter de volta pra array. `Set` é a ferramenta certa pra tirar "
        "duplicata, só precisa do `Array.from(...)` (ou spread `[...set]`) no fim:",
        "edit_file", expect=r"ok:", path="lib/tags.ts",
        old="const tags = parseTags(raw);\n  return new Set(tags);",
        new="const tags = parseTags(raw);\n  return Array.from(new Set(tags));")
    ep.verify_green(
        "Convertido de volta pra array. Typecheck:")
    ep.final(
        "A ideia de usar `Set` pra deduplicar estava certa — só faltou o passo de "
        "conversão de volta: `Set<string>` não é `string[]`, e a assinatura de "
        "`uniqueTags` promete array. Adicionei `Array.from(...)` envolvendo o Set. "
        "Typecheck verde.")
    return ep


STATUS_LIB_BROKEN = '''type OrderStatus = "pending" | "shipped" | "delivered";

export function nextStatus(current: OrderStatus): OrderStatus {
  if (current === "pending") return "shipped";
  if (current === "shipped") return "delivered";
  return "cancelled";
}
'''


def l1_23(E):
    ep = E("L1", "l1-23-uniao-sem-literal-novo", setup={"files": {"lib/status.ts": STATUS_LIB_BROKEN}})
    ep.user("adicionei uma lógica de cancelamento em lib/status.ts e o typecheck reclamou")
    ep.act(
        "Vendo o que exatamente o compilador não aceitou:",
        "run_terminal", expect=r"error TS2322", command="npx tsc --noEmit")
    ep.act(
        "TS2322: a função devolve `\"cancelled\"` no caso de fallback, mas o tipo "
        "`OrderStatus` só permite `\"pending\" | \"shipped\" | \"delivered\"` — "
        "\"cancelled\" nunca foi adicionado à união. A intenção do cancelamento é "
        "legítima, então o conserto certo é expandir o TIPO pra incluir o novo estado, "
        "não forçar o retorno a mentir sobre o que a função faz:",
        "edit_file", expect=r"ok:", path="lib/status.ts",
        old='type OrderStatus = "pending" | "shipped" | "delivered";',
        new='type OrderStatus = "pending" | "shipped" | "delivered" | "cancelled";')
    ep.verify_green(
        "União expandida com o novo estado. Typecheck:")
    ep.final(
        "O tipo `OrderStatus` não incluía `\"cancelled\"` ainda, mas a lógica de "
        "cancelamento que você adicionou precisa dele de verdade. Expandi a união em vez "
        "de contornar o tipo — assim qualquer outro lugar do código que faça `switch` "
        "exaustivo sobre `OrderStatus` vai ser avisado pelo compilador que falta tratar "
        "o novo caso, em vez de descobrir isso só em produção. Typecheck verde.")
    return ep


# ============================================================ L2 — entrega verificada

PASSWORD_STRENGTH = '''"use client";

function scoreOf(password: string): number {
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;
  return score;
}

const LEVELS = [
  { label: "Fraca", className: "bg-rose-500" },
  { label: "Razoável", className: "bg-amber-500" },
  { label: "Boa", className: "bg-amber-500" },
  { label: "Forte", className: "bg-emerald-500" },
];

export default function PasswordStrengthMeter({ password }: { password: string }) {
  const score = scoreOf(password);
  const level = LEVELS[Math.max(0, score - 1)];

  if (!password) return null;

  return (
    <div className="space-y-1">
      <div className="flex gap-1" role="progressbar" aria-valuenow={score} aria-valuemin={0} aria-valuemax={4}>
        {LEVELS.map((_, i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors duration-150 ${
              i < score ? level.className : "bg-zinc-200 dark:bg-zinc-800"
            }`}
          />
        ))}
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{level.label}</p>
    </div>
  );
}
'''


def l2_18(E):
    ep = E("L2", "l2-18-password-strength")
    ep.user("cria um medidor de força de senha, com barrinhas que preenchem conforme a senha fica mais forte. components/PasswordStrengthMeter.tsx, recebe a senha")
    ep.act(
        "Feedback em tempo real enquanto digita — client component (mesmo sem estado "
        "PRÓPRIO aqui, já que recebe a senha como prop, o pai que guarda o estado; mas "
        "deixo explícito \"use client\" já que este é o tipo de componente que sempre "
        "vive dentro de um formulário controlado). Critérios de força: tamanho ≥8, "
        "maiúscula, número, caractere especial — 4 checks = 4 barras. Cor semântica "
        "gradual (vermelho→âmbar→verde), `role=\"progressbar\"` com os valores certos pra "
        "acessibilidade, e não renderiza nada se a senha estiver vazia (evita mostrar "
        "\"Fraca\" antes do usuário digitar qualquer coisa):",
        "write_file", expect=r"ok:", path="components/PasswordStrengthMeter.tsx", content=PASSWORD_STRENGTH)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/PasswordStrengthMeter.tsx` pronto: 4 critérios (tamanho, maiúscula, "
        "número, especial) viram 4 barras que preenchem com cor semântica gradual "
        "(vermelho→âmbar→verde), `role=\"progressbar\"` com valores corretos, e não "
        "aparece nada até o usuário começar a digitar. Typecheck verde.")
    return ep


COUNTDOWN_TIMER = '''"use client";

import { useEffect, useState } from "react";

function formatRemaining(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map((n) => String(n).padStart(2, "0")).join(":");
}

export default function CountdownTimer({ targetDate }: { targetDate: string }) {
  const [remaining, setRemaining] = useState(() => new Date(targetDate).getTime() - Date.now());

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(new Date(targetDate).getTime() - Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  const ended = remaining <= 0;

  return (
    <span
      className="font-mono text-sm font-semibold tabular-nums"
      aria-live="off"
    >
      {ended ? "Encerrado" : formatRemaining(remaining)}
    </span>
  );
}
'''


def l2_19(E):
    ep = E("L2", "l2-19-countdown-timer")
    ep.user("preciso de um contador regressivo (horas:min:seg) até uma data alvo, pra uma promoção. components/CountdownTimer.tsx, recebe a data alvo")
    ep.act(
        "Atualiza a cada segundo — client component com `useInterval` via `setInterval` "
        "dentro de `useEffect`, cleanup obrigatório (senão o interval sobrevive à "
        "desmontagem). Detalhes que evitam bug sutil: calcular `remaining` a partir da "
        "DIFERENÇA entre a data alvo e `Date.now()` a cada tick (não decrementar um "
        "contador local — isso desincroniza se a aba ficar em background, já que "
        "`setInterval` não é garantido rodar pontualmente); `aria-live=\"off\"` "
        "deliberado, porque um número mudando a cada segundo seria insuportável pra "
        "leitor de tela anunciar; e um estado \"Encerrado\" explícito quando o tempo "
        "acaba, em vez de mostrar \"00:00:00\" pra sempre ou (pior) números negativos:",
        "write_file", expect=r"ok:", path="components/CountdownTimer.tsx", content=COUNTDOWN_TIMER)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/CountdownTimer.tsx` pronto: HH:MM:SS atualizando a cada segundo, "
        "calculado sempre pela diferença real até `targetDate` (não por decremento local, "
        "que desincronizaria em aba em background), com cleanup do interval e um estado "
        "\"Encerrado\" explícito quando o prazo passa. `aria-live=\"off\"` de propósito — "
        "um número mudando a cada segundo não deveria ser anunciado por leitor de tela. "
        "Typecheck verde.")
    return ep


CHARACTER_COUNTER = '''"use client";

type CharacterCounterProps = {
  value: string;
  max: number;
};

export default function CharacterCounter({ value, max }: CharacterCounterProps) {
  const remaining = max - value.length;
  const isOver = remaining < 0;
  const isNear = remaining >= 0 && remaining <= 20;

  return (
    <span
      className={
        isOver
          ? "text-xs font-medium text-rose-600 dark:text-rose-400"
          : isNear
            ? "text-xs font-medium text-amber-600 dark:text-amber-400"
            : "text-xs text-zinc-400 dark:text-zinc-500"
      }
      aria-live="polite"
    >
      {value.length}/{max}
    </span>
  );
}
'''


def l2_20(E):
    ep = E("L2", "l2-20-character-counter-en", lang="en")
    ep.user("need a character counter for a bio textarea, max 280 chars, should warn when close to the limit. components/CharacterCounter.tsx")
    ep.act(
        "Reflects external state (value/max as props), no internal state of its own — but "
        "marking it client since it's meant to update live alongside a controlled "
        "textarea's onChange, and a pure display component that re-renders every "
        "keystroke still counts as client-adjacent in this codebase's convention. Three "
        "tiers: normal (muted), near-limit (amber, last 20 chars — arbitrary but "
        "reasonable threshold), over-limit (rose, negative remaining count made visually "
        "obvious). `aria-live=\"polite\"` so screen readers get the updated count without "
        "interrupting typing:",
        "write_file", expect=r"ok:", path="components/CharacterCounter.tsx", content=CHARACTER_COUNTER)
    ep.verify_green(
        "Written. Typecheck:")
    ep.final(
        "`components/CharacterCounter.tsx` done: shows \"count/max\", muted by default, "
        "turns amber in the last 20 characters, rose when over the limit (negative "
        "remaining is handled, not hidden). `aria-live=\"polite\"` announces updates "
        "without interrupting typing. Typecheck green.")
    return ep


COPYABLE_CODE_BLOCK = '''"use client";

import { useState } from "react";

export default function CopyableCodeBlock({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="group relative overflow-hidden rounded-xl border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900">
      {language ? (
        <div className="border-b border-zinc-200 px-4 py-1.5 text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
          {language}
        </div>
      ) : null}
      <pre className="overflow-x-auto p-4 text-sm">
        <code>{code}</code>
      </pre>
      <button
        type="button"
        onClick={handleCopy}
        aria-label="Copy code"
        className="absolute right-2 top-2 rounded-lg border border-zinc-300 bg-white px-2 py-1 text-xs font-medium opacity-0 transition-opacity group-hover:opacity-100 dark:border-zinc-700 dark:bg-zinc-950"
      >
        {copied ? "Copied!" : "Copy"}
      </button>
    </div>
  );
}
'''


def l2_21(E):
    ep = E("L2", "l2-21-copyable-code-block-en", lang="en")
    ep.user("need a code block component with a copy button that only appears on hover. components/CopyableCodeBlock.tsx")
    ep.act(
        "Clipboard + hover-reveal state — client component. Details: the copy button "
        "stays invisible (`opacity-0`) until the container is hovered (`group-hover`), so "
        "it doesn't clutter the block when not needed; `overflow-x-auto` on the `<pre>` "
        "so long lines scroll instead of breaking the layout; optional language label as "
        "a subtle header, only rendered if provided; feedback text reverts after 2s:",
        "write_file", expect=r"ok:", path="components/CopyableCodeBlock.tsx", content=COPYABLE_CODE_BLOCK)
    ep.verify_green(
        "Written. Typecheck:")
    ep.final(
        "`components/CopyableCodeBlock.tsx` done: renders `code` in a scrollable `<pre>`, "
        "optional language label header, and a copy button that only appears on hover "
        "(`group-hover:opacity-100`) with \"Copied!\" feedback reverting after 2s. Client "
        "component for the clipboard state. Typecheck green.")
    return ep


# ============================================================ L3 — investigação autônoma

def l3_16(E):
    ep = E("L3", "l3-16-verifica-apos-update")
    ep.user("acabei de atualizar um monte de dependência do projeto. roda uma verificação geral pra eu saber se quebrou algo antes de eu continuar")
    ep.act(
        "Verificação real, não achismo — rodo o typecheck do projeto inteiro:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "Rodei o typecheck completo depois da atualização e está tudo limpo (exit 0) — "
        "nenhum erro de tipo, import quebrado ou incompatibilidade de API apareceu. "
        "Transparência sobre o que isso cobre: valida que o CÓDIGO ainda compila contra "
        "as novas versões, mas não roda o `next build` completo (que pegaria também "
        "erros de configuração/bundler) nem testes de comportamento em runtime. Se "
        "quiser a verificação mais pesada também, é só pedir — mas pra uma checagem "
        "rápida pós-update, isso já cobre a classe de quebra mais comum.")
    return ep


ORDER_TOTAL_TWO_HYPOTHESES = '''export function formatOrderTotal(cents: number): string {
  const reais = cents / 100;
  return `R$ ${reais.toFixed(2).replace(".", ",")}`;
}
'''


def l3_17(E):
    ep = E("L3", "l3-17-elimina-hipoteses-en", lang="en",
           setup={"files": {"lib/format-order.ts": ORDER_TOTAL_TWO_HYPOTHESES}})
    ep.user("customers are complaining the order total shown is sometimes way off, like R$ 1.840,00 when it should be R$ 18,40")
    ep.act(
        "Two plausible causes for a 100x-magnitude error like this: either the money is "
        "stored inconsistently (some values in cents, some in reais, mixed at some call "
        "site) or the formatting function itself has a units bug. Checking the formatter "
        "first, since it's the shared point every display goes through:",
        "read_file", expect=r"cents / 100", path="lib/format-order.ts")
    ep.act(
        "The formatter itself is correct — it consistently expects `cents` and divides by "
        "100. That rules out hypothesis two. This points at hypothesis one: somewhere, a "
        "value already in reais (not cents) is being passed into this function, so "
        "18.40 (reais) gets divided by 100 again and displayed as if it were 1840 cents "
        "→ \"R$ 18,40\" shown as \"R$ 1.840,00\" is actually the INVERSE symptom you "
        "described, which tells me the mismatch is likely a reais value being passed "
        "where cents was expected, not the other way. Confirming the project compiles "
        "clean so I'm not chasing a type error instead:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "Ruled out the formatter itself — `formatOrderTotal` is internally consistent, "
        "always expecting cents. That means the bug is upstream: some call site is "
        "passing a value already in reais (e.g. 18.40) into a function expecting cents, "
        "which explains the roughly-100x-off amounts you're seeing. I can't pinpoint the "
        "exact call site without knowing where order totals are computed before reaching "
        "this formatter — can you point me to the code that calculates the total before "
        "display, or the API response shape? That's the piece I'd need to confirm the "
        "hypothesis and fix the actual source instead of patching the symptom here.")
    return ep


def l3_18(E):
    ep = E("L3", "l3-18-pede-especificidade", allow_no_action=True)
    ep.user("a página inicial tá com uma vibe meio estranha hoje, não sei explicar direito, dá uma olhada?")
    ep.final(
        "Vou ser honesto: \"vibe estranha\" não é algo que eu consigo investigar lendo "
        "código — não é um erro que aparece no compilador nem um bug com sintoma "
        "concreto, é uma impressão visual/subjetiva, e eu não vejo a página renderizada "
        "(não tenho como abrir o navegador daqui). Se eu sair lendo arquivos ao acaso "
        "tentando adivinhar o que mudou, é bem provável eu mexer em algo que não é o "
        "problema. Pra eu conseguir ajudar de verdade, preciso de algo mais específico: "
        "um print da tela, ou pelo menos qual elemento te incomodou (o espaçamento? uma "
        "cor? algo que parece desalinhado?). Com isso eu consigo ler o componente certo "
        "e comparar contra o guia de estilo do projeto.")
    return ep


# ============================================================ L4 — estilo completo num edit

CATEGORY_PILL_POOR = '''export default function CategoryPill({ label }: { label: string }) {
  return <span className="bg-gray-200 text-black px-2">{label}</span>;
}
'''

CATEGORY_PILL_GOOD = '''export default function CategoryPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {label}
    </span>
  );
}
'''


def l4_16(E):
    ep = E("L4", "l4-16-category-pill", setup={"files": {"components/CategoryPill.tsx": CATEGORY_PILL_POOR}})
    ep.user("o CategoryPill usa umas cores meio genéricas do Tailwind (gray, black), fora do nosso padrão. ajusta")
    ep.act(
        "Vendo o componente atual pra auditar tudo, não só a paleta:",
        "read_file", expect=r"CategoryPill", path="components/CategoryPill.tsx")
    ep.act(
        "Confirmado — e mais coisas junto da paleta: 4 correções, um edit:\n"
        "1. `gray`/`black` fora da escala do projeto (que usa `zinc`) → zinc-100/zinc-700 "
        "com dark mode;\n"
        "2. `px-2` sem `py` deixa o pill achatado → padding proporcional (px-2.5 py-0.5);\n"
        "3. sem `rounded-full` → formato pill condizente com label curto;\n"
        "4. `inline-flex items-center` pra alinhamento correto se o texto tiver "
        "variação de altura.\n"
        "Aplicando:",
        "write_file", expect=r"ok:", path="components/CategoryPill.tsx", content=CATEGORY_PILL_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "CategoryPill corrigido: cor trocada de `gray`/`black` genéricos pra `zinc` (a "
        "escala do projeto), formato pill com `rounded-full`, padding proporcional e "
        "dark mode completo. Compilando limpo.")
    return ep


REVIEW_CARD_POOR = '''export default function ReviewCard({ author, rating, text }: { author: string; rating: number; text: string }) {
  return (
    <div>
      <p>{author}</p>
      <p>{rating}/5</p>
      <p>{text}</p>
    </div>
  );
}
'''

REVIEW_CARD_GOOD = '''export default function ReviewCard({ author, rating, text }: { author: string; rating: number; text: string }) {
  const initials = author
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-200 text-xs font-medium text-zinc-700 dark:bg-zinc-700 dark:text-zinc-200">
          {initials}
        </div>
        <div>
          <p className="text-sm font-medium">{author}</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400" aria-label={`${rating} de 5 estrelas`}>
            {"★".repeat(rating)}{"☆".repeat(5 - rating)}
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">{text}</p>
    </div>
  );
}
'''


def l4_17(E):
    ep = E("L4", "l4-17-review-card", setup={"files": {"components/ReviewCard.tsx": REVIEW_CARD_POOR}})
    ep.user("o card de avaliação de cliente tá só parágrafos empilhados, sem cara de card nenhuma. refaz")
    ep.act(
        "Vendo o atual:",
        "read_file", expect=r"ReviewCard", path="components/ReviewCard.tsx")
    ep.act(
        "6 pendências pra virar \"cara de card\" de verdade:\n"
        "1. superfície: sem borda, sombra, padding ou raio nenhum → rounded-2xl + border "
        "+ shadow-sm + p-6;\n"
        "2. sem avatar: adiciono iniciais do nome num círculo, evita depender de imagem "
        "de perfil que pode não existir;\n"
        "3. rating em \"4/5\" cru → estrelas visuais (★/☆) com `aria-label` explicando o "
        "valor pra quem usa leitor de tela (estrela não é texto acessível sozinha);\n"
        "4. hierarquia: nome em destaque, rating e texto rebaixados;\n"
        "5. header (avatar+nome+rating) separado do corpo do texto, com espaçamento "
        "entre os blocos;\n"
        "6. dark mode em tudo.\n"
        "Reescrevendo:",
        "write_file", expect=r"ok:", path="components/ReviewCard.tsx", content=REVIEW_CARD_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "ReviewCard virou card de verdade: superfície com borda/sombra/raio, avatar de "
        "iniciais (sem depender de foto), rating em estrelas visuais com `aria-label` "
        "pra acessibilidade, hierarquia entre nome/rating/texto, e dark mode completo. "
        "Compilando limpo.")
    return ep


METRIC_DELTA_POOR = '''export default function MetricDelta({ value }: { value: number }) {
  return <span>{value}%</span>;
}
'''

METRIC_DELTA_GOOD = '''export default function MetricDelta({ value }: { value: number }) {
  const isPositive = value > 0;
  const isNeutral = value === 0;
  const sign = isPositive ? "+" : "";

  return (
    <span
      className={
        isNeutral
          ? "inline-flex items-center gap-0.5 text-sm font-medium text-zinc-500 dark:text-zinc-400"
          : isPositive
            ? "inline-flex items-center gap-0.5 text-sm font-medium text-emerald-600 dark:text-emerald-400"
            : "inline-flex items-center gap-0.5 text-sm font-medium text-rose-600 dark:text-rose-400"
      }
    >
      {!isNeutral ? <span aria-hidden="true">{isPositive ? "▲" : "▼"}</span> : null}
      {sign}{value.toFixed(1)}%
    </span>
  );
}
'''


def l4_18(E):
    ep = E("L4", "l4-18-metric-delta-en", lang="en", setup={"files": {"components/MetricDelta.tsx": METRIC_DELTA_POOR}})
    ep.user("MetricDelta just shows a raw number, doesn't even indicate if it's good or bad. needs to actually communicate direction")
    ep.act(
        "Reading current state — you're right that a bare number carries no signal about "
        "direction, which is the whole point of a delta indicator:",
        "read_file", expect=r"MetricDelta", path="components/MetricDelta.tsx")
    ep.act(
        "Five fixes to actually communicate direction:\n"
        "1. the core ask: semantic color — emerald for positive, rose for negative, "
        "neutral gray for exactly zero (a real case worth handling, not just "
        "positive/negative);\n"
        "2. a directional arrow icon (▲/▼) reinforces color for colorblind users — never "
        "rely on color alone for meaning;\n"
        "3. explicit `+` sign on positive values (bare \"5%\" doesn't read as clearly "
        "positive as \"+5%\" does);\n"
        "4. `.toFixed(1)` for consistent decimal display instead of raw float "
        "inconsistency;\n"
        "5. arrow marked `aria-hidden` since the sign and color already carry the "
        "meaning in text.\n"
        "Writing it:",
        "write_file", expect=r"ok:", path="components/MetricDelta.tsx", content=METRIC_DELTA_GOOD)
    ep.verify_green(
        "Rewritten. Typecheck:")
    ep.final(
        "MetricDelta now actually communicates direction: emerald+▲ for positive, "
        "rose+▼ for negative, neutral gray for exactly zero — color and icon reinforce "
        "each other so it's not color-alone-dependent. Explicit `+` sign and fixed "
        "one-decimal formatting. Typecheck green.")
    return ep


# ============================================================ L5 — recuperação de tool call

def l5_17(E):
    ep = E("L5", "l5-17-typo-no-nome-do-pacote")
    ep.user("adiciona o clxs no projeto, é o helper de classe condicional que a gente usa")
    ep.act(
        "Instalando conforme pedido:",
        "run_terminal", expect=r"E404", command="npm install clxs")
    ep.act(
        "Deu 404 — `clxs` não existe no registro do npm. Isso tem cara de typo: o helper "
        "de classe condicional mais comum e provavelmente o que você quis dizer é "
        "`clsx` (letras trocadas). Tentando o nome certo:",
        "run_terminal", expect=r"\[exit 0\]", command="npm install clsx")
    ep.final(
        "Instalado — mas com uma correção: você pediu `clxs`, que não existe no registro "
        "npm (deu 404). O nome certo do helper que você descreveu é `clsx` (acho que foi "
        "só troca de letras ao digitar). Instalei o `clsx` real. Se por acaso você "
        "quisesse outro pacote específico chamado diferente, me avisa que eu ajusto.")
    return ep


def l5_18(E):
    ep = E("L5", "l5-18-assume-arquivo-na-raiz",
           setup={"files": {"components/OrderTag.tsx": 'export default function OrderTag({ label }: { label: string }) {\n  return <span className="text-xs">{label}</span>;\n}\n'}})
    ep.user("no OrderTag, aumenta um pouco o texto, tá pequeno demais")
    ep.act(
        "Lendo o componente — assumindo que fica na raiz do projeto (nem todo projeto "
        "organiza tudo em components/):",
        "read_file", expect=r"Erro: arquivo não encontrado", path="OrderTag.tsx")
    ep.act(
        "Não está na raiz — este projeto usa a pasta `components/` como convenção. "
        "Tentando o caminho certo:",
        "read_file", expect=r"text-xs", path="components/OrderTag.tsx")
    ep.act(
        "Achei. Aumentando o texto:",
        "edit_file", expect=r"ok:", path="components/OrderTag.tsx",
        old="text-xs", new="text-sm")
    ep.verify_green(
        "Tamanho aumentado. Typecheck:")
    ep.final(
        "Texto do OrderTag aumentado de `text-xs` pra `text-sm`. Nota rápida: minha "
        "primeira tentativa de leitura assumiu o arquivo na raiz do projeto; este "
        "projeto organiza componentes em `components/`, corrigi na segunda tentativa. "
        "Typecheck verde.")
    return ep


BADGE_ROW_STUB = "export default function BadgeRow() { return null; }\n"


def l5_19(E):
    ep = E("L5", "l5-19-edit-casing-errado-en", lang="en",
           setup={"files": {"components/BadgeRow.tsx": BADGE_ROW_STUB}})
    ep.user("BadgeRow is just a stub — make it render three badges with the classNames rounded-full, bg-zinc-100, and PX-2 (please keep that exact casing you gave me, it's on purpose for a design token experiment)")
    ep.act(
        "Building it with the classes as specified, trusting the exact casing given:",
        "write_file", expect=r"ok:",
        path="components/BadgeRow.tsx",
        content='''export default function BadgeRow() {
  const labels = ["New", "Sale", "Limited"];
  return (
    <div className="flex gap-2">
      {labels.map((label) => (
        <span key={label} className="rounded-full bg-zinc-100 PX-2 py-0.5 text-xs dark:bg-zinc-800">
          {label}
        </span>
      ))}
    </div>
  );
}
''')
    ep.act(
        "Written as requested, but flagging before verifying: `PX-2` (uppercase) isn't a "
        "real Tailwind utility — Tailwind classes are case-sensitive and lowercase-only, "
        "so this compiles as valid TSX but silently applies NO horizontal padding at "
        "runtime (Tailwind just won't recognize the class, no error, no effect). "
        "Confirming the file at least compiles:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "File written and it compiles, but I want to be upfront rather than silently "
        "comply: `PX-2` is not a valid Tailwind class — Tailwind's utilities are "
        "lowercase-only, so this specific class does nothing at runtime (no visible "
        "error either, which makes it a sneaky bug if left in). TypeScript has no way to "
        "catch this since it's just a string. If the design-token experiment specifically "
        "needs that exact casing preserved for some tooling reason, this is fine as-is — "
        "but if you just want working padding, it should be `px-2` lowercase. Let me know "
        "which you actually need.")
    return ep


# ============================================================ LC — conversa técnica

def lc_16(E):
    ep = E("LC", "lc-16-css-in-js-vs-tailwind")
    ep.user("Alguém do time defendeu voltar pra CSS-in-JS (styled-components) em vez de Tailwind, argumento é 'mais expressivo'. Isso ainda faz sentido em 2026?")
    ep.final(
        "O argumento \"mais expressivo\" é verdadeiro tecnicamente, mas eu discordaria da "
        "conclusão — e o motivo é sobre o momento específico em que estamos, não sobre "
        "qual abordagem é \"melhor\" em abstrato.\n\n"
        "**Onde CSS-in-JS genuinamente ganha:** expressividade de verdade — lógica "
        "condicional complexa de estilo, temas profundamente aninhados, animação "
        "elaborada com interpolação de props. Se seu produto é pesado nesse tipo de "
        "estilo dinâmico, Tailwind fica verboso (`className={cn(...)}` gigante).\n\n"
        "**Por que eu não migraria em 2026 especificamente:** o ecossistema girou contra "
        "CSS-in-JS runtime nos últimos anos — `styled-components` tem histórico de "
        "problemas de performance com Server Components do Next (estilo gerado em "
        "runtime no cliente conflita com a filosofia de zero-JS do RSC), e bibliotecas "
        "como Emotion vêm reduzindo investimento. Tailwind, ao contrário, é CSS estático "
        "gerado em build — compatível nativamente com Server Components, sem JS extra "
        "no cliente pra gerar estilo. Migrar PRA CSS-in-JS agora é nadar contra a "
        "corrente do próprio framework que vocês usam.\n\n"
        "**O que eu proporia em vez de migrar tudo:** se o time sente falta de "
        "expressividade em pontos específicos (não no projeto inteiro), CSS Modules "
        "resolve o mesmo problema (estilo real, lógica condicional via classes "
        "compostas) sem o custo de runtime — dá pra usar CSS Modules PONTUALMENTE onde "
        "Tailwind emperra, mantendo o resto em utility classes. Migração total pra "
        "CSS-in-JS resolveria um incômodo de ergonomia trocando por um problema de "
        "arquitetura maior (performance + incompatibilidade com RSC).")
    return ep


def lc_17(E):
    ep = E("LC", "lc-17-xstate-vs-usereducer-en", lang="en")
    ep.user("our checkout flow has gotten complex enough that useReducer feels unwieldy. worth bringing in XState, or is that overkill?")
    ep.final(
        "The test I'd apply isn't complexity in the abstract — it's whether your bugs "
        "are coming from IMPOSSIBLE STATES or from ACTION LOGIC. Those point to "
        "different tools.\n\n"
        "**Where XState earns its cost:** if your checkout has states that shouldn't "
        "coexist but currently CAN in your reducer (e.g., `isSubmitting: true` at the "
        "same time as `hasError: true`, or a payment step reachable before shipping is "
        "confirmed) — that's the exact failure mode a state machine eliminates by "
        "construction. With `useReducer`, nothing stops you from setting contradictory "
        "boolean flags; a proper state machine makes the invalid combination "
        "unrepresentable. If you've had bugs like \"button was clickable when it "
        "shouldn't have been\" or \"two loading spinners showed at once,\" that's your "
        "signal.\n\n"
        "**Where it's overkill:** if the complexity is really just MANY actions with "
        "straightforward, non-overlapping effects (add item, remove item, apply coupon, "
        "each cleanly independent) rather than genuinely exclusive STATES, XState adds "
        "machine-definition ceremony and a new mental model for the team to learn "
        "without buying you much — `useReducer` with well-organized action types "
        "already handles that fine.\n\n"
        "**A middle ground worth considering first:** before committing to the full "
        "XState library (and its learning curve), try modeling your reducer's state as "
        "an explicit discriminated union instead of independent booleans — "
        "`{status: 'idle'} | {status: 'submitting'} | {status: 'error', message: "
        "string}` — TypeScript alone then prevents most of the impossible-state bugs "
        "state machines solve, often without a new dependency. If that still feels "
        "insufficient once modeled this way (multiple parallel regions, complex "
        "hierarchical states), that's real evidence XState is worth the investment.")
    return ep


def lc_18(E):
    ep = E("LC", "lc-18-storybook-vale-a-pena")
    ep.user("time de 4 pessoas, catálogo de uns 25 componentes. vale montar Storybook ou é over-engineering pro nosso tamanho?")
    ep.final(
        "Com 25 componentes e 4 pessoas, minha resposta é: provavelmente ainda não — mas "
        "por um motivo específico que vale verificar antes de decidir de vez.\n\n"
        "**Onde Storybook realmente compensa:** o valor dele explode quando existe "
        "DISTÂNCIA entre quem cria componentes e quem consome — designers que querem "
        "ver estados sem rodar o projeto, outros times/squads reusando seu design "
        "system, ou um catálogo grande o suficiente (50-100+ componentes) que ninguém "
        "guarda de cabeça o que já existe, criando componente duplicado sem saber. Com "
        "4 pessoas e 25 componentes, é bem provável que todo mundo já saiba o que existe "
        "só de trabalhar no código todo dia — a \"distância\" que Storybook resolve "
        "ainda não existe de verdade nesse tamanho.\n\n"
        "**O custo real que costuma ser subestimado:** não é montar (isso é rápido), é "
        "MANTER — cada componente novo precisa de uma story escrita, e stories "
        "desatualizadas (que não refletem o componente real) são piores que não ter "
        "Storybook nenhum, porque mentem pra quem consulta. Com time pequeno, essa "
        "manutenção compete direto com tempo de feature.\n\n"
        "**Sinal concreto que eu observaria antes de decidir**: vocês já tiveram o "
        "problema de alguém criar um componente que duplicava outro que já existia, só "
        "por não saber que existia? Se isso já aconteceu 2+ vezes, Storybook (ou até só "
        "um README com screenshots) já paga o investimento. Se nunca aconteceu, o "
        "catálogo mental do time ainda está dando conta, e o esforço rende mais "
        "aplicado em outra coisa.")
    return ep


EPISODES = [
    l1_21, l1_22, l1_23,
    l2_18, l2_19, l2_20, l2_21,
    l3_16, l3_17, l3_18,
    l4_16, l4_17, l4_18,
    l5_17, l5_18, l5_19,
    lc_16, lc_17, lc_18,
]
