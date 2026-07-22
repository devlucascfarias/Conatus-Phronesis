# -*- coding: utf-8 -*-
"""Batch e005 — 20 episódios. Códigos TS confirmados por execução real ANTES da CoT:
TS2588 (reatribuição de const), TS2365 (await faltando, Promise em aritmética),
TS2323/2393 (identificador duplicado). Cenários de L5 (path aninhado errado, extensão
errada, content não-string) confirmados via probe isolado.
"""

# ============================================================ L1 — ciclo completo

LIMITS_LIB_BROKEN = '''export function computeMaxItems(base: number, bonus: number): number {
  const maxItems = base;
  if (bonus > 0) {
    maxItems = base + bonus;
  }
  return maxItems;
}
'''


def l1_17(E):
    ep = E("L1", "l1-17-const-reassign", setup={"files": {"lib/limits.ts": LIMITS_LIB_BROKEN}})
    ep.user("lib/limits.ts não compila, adicionei a lógica de bônus rapidão")
    ep.act(
        "Vendo o que a adição do bônus quebrou:",
        "run_terminal", expect=r"error TS2588", command="npx tsc --noEmit")
    ep.act(
        "TS2588: `maxItems` foi declarada `const` mas o código tenta reatribuir dentro do "
        "`if`. A intenção é clara — o valor muda condicionalmente — então o certo é "
        "declarar como `let`, não forçar uma reescrita mais complexa só pra manter `const`:",
        "edit_file", expect=r"ok:", path="lib/limits.ts",
        old="const maxItems = base;", new="let maxItems = base;")
    ep.verify_green(
        "Declaração corrigida pro que o código realmente faz. Typecheck:")
    ep.final(
        "Era TS2588: `maxItems` era `const`, mas a lógica de bônus que você adicionou "
        "reatribui o valor dentro do `if`. Troquei pra `let` — é exatamente o caso de uso "
        "que `let` existe pra cobrir (valor que muda condicionalmente), não faz sentido "
        "reescrever a lógica só pra preservar `const` à força. Typecheck verde.")
    return ep


PRICING_LIB_BROKEN = '''async function fetchTaxRate(): Promise<number> {
  return 0.08;
}

export async function priceWithTax(amount: number): Promise<string> {
  const rate = fetchTaxRate();
  return (amount * (1 + rate)).toFixed(2);
}
'''


def l1_18(E):
    ep = E("L1", "l1-18-await-faltando", setup={"files": {"lib/pricing.ts": PRICING_LIB_BROKEN}})
    ep.user("lib/pricing.ts tá dando erro estranho de tipo numérico, mas os números tão certos")
    ep.act(
        "\"Números certos\" mas erro de tipo é sinal de que o valor em si não é o número "
        "que parece ser. Confiro o erro exato:",
        "run_terminal", expect=r"error TS2365", command="npx tsc --noEmit")
    ep.act(
        "TS2365: operação `+` entre `1` e `Promise<number>` — ou seja, `rate` não é o "
        "número 0.08, é a PROMESSA de um número. `fetchTaxRate` é `async`, e "
        "`const rate = fetchTaxRate()` esqueceu o `await`. Sem ele, `rate` é um objeto "
        "Promise, não o valor resolvido — daí a aritmética quebrar:",
        "edit_file", expect=r"ok:", path="lib/pricing.ts",
        old="const rate = fetchTaxRate();", new="const rate = await fetchTaxRate();")
    ep.verify_green(
        "Await adicionado. Typecheck:")
    ep.final(
        "O \"erro estranho\" era `await` faltando: `fetchTaxRate()` é `async`, e sem "
        "`await` a variável `rate` guardava a Promise em si, não o número resolvido — daí "
        "o TS2365 ao tentar somar `1 + Promise<number>`. Os números que você via certos no "
        "código-fonte nunca chegavam a ser usados de fato; a função ia quebrar em runtime "
        "antes mesmo de calcular. Adicionei o `await`. Typecheck verde.")
    return ep


FORMAT_LIB_BROKEN = '''export function formatWeight(kg: number): string {
  return `${kg.toFixed(1)} kg`;
}

export function formatWeight(kg: number, unit: string): string {
  return `${kg.toFixed(1)} ${unit}`;
}
'''


def l1_19(E):
    ep = E("L1", "l1-19-identificador-duplicado", setup={"files": {"lib/format.ts": FORMAT_LIB_BROKEN}})
    ep.user("lib/format.ts não builda, acho que dei merge errado e duplicou algo")
    ep.act(
        "Merge duplicando código é bem plausível — confiro o que o compilador aponta:",
        "run_terminal", expect=r"error TS2393", command="npx tsc --noEmit")
    ep.act(
        "TS2323/TS2393: `formatWeight` está declarada DUAS vezes no arquivo, com "
        "assinaturas diferentes (uma com `unit`, outra sem). Bate com sua suspeita de "
        "merge. As duas versões fazem sentido de existir — uma assume \"kg\" fixo, a "
        "outra aceita a unidade — então a solução certa não é apagar uma, é dar nomes "
        "diferentes pras duas ao invés de sobrecarga de função (que complicaria à toa "
        "pra esse caso simples):",
        "edit_file", expect=r"ok:", path="lib/format.ts",
        old="export function formatWeight(kg: number, unit: string): string {\n  return `${kg.toFixed(1)} ${unit}`;\n}",
        new="export function formatWeightWithUnit(kg: number, unit: string): string {\n  return `${kg.toFixed(1)} ${unit}`;\n}")
    ep.verify_green(
        "Renomeada pra não colidir. Typecheck:")
    ep.final(
        "Confirmado: merge duplicou a função `formatWeight` com duas assinaturas "
        "diferentes no mesmo arquivo (TS2323/2393). Como as duas versões servem a "
        "propósitos ligeiramente diferentes (uma fixa \"kg\", a outra aceita a unidade), "
        "renomeei a segunda pra `formatWeightWithUnit` em vez de descartar uma das duas — "
        "nenhuma lógica foi perdida. Typecheck verde. Vale conferir se algum código já "
        "chama a versão com 2 argumentos esperando o nome antigo.")
    return ep


CHECKOUT_SUMMARY_BROKEN = '''type LineItem = { name: string; qty: number; unitPrice: number };

export function computeTotal(items: LineItem[], discountPct: number): number {
  const subtotal = items.reduce((sum, item) => sum + item.qty * item.unitPrice, 0);
  return subtotal - subtotal * discountPct;
}
'''

CHECKOUT_PAGE = '''import { computeTotal } from "@/lib/checkout";

export default function CheckoutPage() {
  const items = [{ name: "Camiseta", qty: 2, unitPrice: 49.9 }];
  const total = computeTotal(items, 10);
  return (
    <main className="mx-auto max-w-2xl px-4 py-16">
      <p>Total: R$ {total.toFixed(2)}</p>
    </main>
  );
}
'''


def l1_20(E):
    ep = E("L1", "l1-20-logica-sem-erro-de-tipo", setup={"files": {
        "lib/checkout.ts": CHECKOUT_SUMMARY_BROKEN,
        "app/checkout/page.tsx": CHECKOUT_PAGE,
    }})
    ep.user("o total do checkout tá saindo negativo quando o desconto é maior que 10, tipo passei 50 e deu valor absurdo. o typecheck passa liso")
    ep.act(
        "Se o typecheck passa, o bug é de LÓGICA, não de tipo — preciso ler o código, não "
        "rodar o compilador de novo:",
        "read_file", expect=r"discountPct", path="lib/checkout.ts")
    ep.act(
        "Achei: `computeTotal` recebe `discountPct` como número \"cru\" (ex.: 10 pra 10%), "
        "mas usa direto em `subtotal * discountPct` sem dividir por 100. Com "
        "`discountPct=10`, isso desconta 1000% do subtotal — exatamente o \"valor "
        "absurdo negativo\" que você viu. A chamada em checkout/page.tsx passa `10` "
        "esperando 10%, então o bug é na função, não no call site:",
        "edit_file", expect=r"ok:", path="lib/checkout.ts",
        old="return subtotal - subtotal * discountPct;",
        new="return subtotal - subtotal * (discountPct / 100);")
    ep.verify_green(
        "Porcentagem convertida corretamente. Typecheck (não pega esse tipo de bug, mas "
        "confirmo que nada quebrou na sintaxe):")
    ep.final(
        "Não era erro de tipo — era lógica: `computeTotal` tratava `discountPct=10` como "
        "1000% de desconto em vez de 10%, porque multiplicava direto sem dividir por 100. "
        "Corrigido pra `discountPct / 100`. Isso é o tipo de bug que o TypeScript nunca "
        "pegaria (os tipos estavam certos o tempo todo) — só apareceu porque você testou "
        "com um valor real e notou o resultado errado.")
    return ep


# ============================================================ L2 — entrega verificada

BACK_TO_TOP = '''"use client";

import { useEffect, useState } from "react";

export default function BackToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    function onScroll() {
      setVisible(window.scrollY > 400);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Voltar ao topo"
      className="fixed bottom-6 right-6 z-40 flex h-11 w-11 items-center justify-center rounded-full bg-zinc-900 text-white shadow-md transition-colors hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300 dark:focus-visible:ring-offset-zinc-950"
    >
      ↑
    </button>
  );
}
'''


def l2_15(E):
    ep = E("L2", "l2-15-back-to-top")
    ep.user("cria um botão de 'voltar ao topo' que só aparece depois que rola um pouco a página. components/BackToTopButton.tsx")
    ep.act(
        "Escuta de scroll + estado — client component. Detalhes: listener com "
        "`{ passive: true }` (scroll é evento de alta frequência, passive evita bloquear o "
        "scroll esperando o handler), cleanup no useEffect pra não vazar listener entre "
        "montagens, `scrollTo({ behavior: \"smooth\" })` em vez de salto seco, "
        "`aria-label` no botão só-ícone, e `z-40` pra ficar acima do conteúdo sem "
        "competir com um header sticky que normalmente usa z-40/50:",
        "write_file", expect=r"ok:", path="components/BackToTopButton.tsx", content=BACK_TO_TOP)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/BackToTopButton.tsx` pronto: fica invisível até 400px de scroll, "
        "então aparece fixo no canto inferior direito. Client component com listener de "
        "scroll passivo (não trava a rolagem) e cleanup correto, `scrollTo` suave, e "
        "`aria-label` no botão só-ícone. Typecheck verde.")
    return ep


READING_TIME = '''function estimateMinutes(wordCount: number): number {
  const wordsPerMinute = 200;
  return Math.max(1, Math.ceil(wordCount / wordsPerMinute));
}

export default function ReadingTime({ text }: { text: string }) {
  const wordCount = text.trim().split(/\\s+/).filter(Boolean).length;
  const minutes = estimateMinutes(wordCount);
  return (
    <span className="text-sm text-zinc-500 dark:text-zinc-400">
      {minutes} min de leitura
    </span>
  );
}
'''


def l2_16(E):
    ep = E("L2", "l2-16-reading-time")
    ep.user("cria um componente que calcula e mostra o tempo estimado de leitura de um texto (tipo blog). components/ReadingTime.tsx, recebe o texto")
    ep.act(
        "Cálculo puro a partir de uma prop — sem estado, server component. A parte que "
        "merece cuidado é a contagem de palavras: `split(/\\s+/)` sozinho pode gerar "
        "strings vazias se o texto tiver espaços múltiplos ou começar/terminar com espaço, "
        "então filtro os vazios antes de contar. `Math.ceil` arredonda pra cima (1,2 min "
        "vira 2, nunca subestima) e `Math.max(1, ...)` garante que texto curtíssimo não "
        "mostre \"0 min\":",
        "write_file", expect=r"ok:", path="components/ReadingTime.tsx", content=READING_TIME)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/ReadingTime.tsx` pronto: recebe `text`, conta palavras (filtrando "
        "espaços múltiplos que gerariam entradas vazias) e estima a 200 palavras/minuto — "
        "métrica padrão de leitura em voz silenciosa. Arredonda sempre pra cima "
        "(`Math.ceil`) e nunca mostra \"0 min\" mesmo pra texto curtíssimo (`Math.max(1, "
        "...)`). Server component, sem estado. Typecheck verde.")
    return ep


EXPANDABLE_TEXT = '''"use client";

import { useState } from "react";

type ExpandableTextProps = {
  text: string;
  maxChars?: number;
};

export default function ExpandableText({ text, maxChars = 180 }: ExpandableTextProps) {
  const [expanded, setExpanded] = useState(false);
  const needsTruncation = text.length > maxChars;
  const shown = expanded || !needsTruncation ? text : `${text.slice(0, maxChars).trimEnd()}…`;

  return (
    <p className="text-sm text-zinc-600 dark:text-zinc-400">
      {shown}{" "}
      {needsTruncation ? (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="font-medium text-zinc-900 underline-offset-4 transition-colors hover:underline dark:text-zinc-100"
        >
          {expanded ? "ler menos" : "ler mais"}
        </button>
      ) : null}
    </p>
  );
}
'''


def l2_17(E):
    ep = E("L2", "l2-17-expandable-text-en", lang="en")
    ep.user("need a paragraph that truncates with 'read more' and expands on click. components/ExpandableText.tsx")
    ep.act(
        "Toggle state — client component. The detail that matters: don't show the "
        "\"read more\" button at all if the text is already shorter than the truncation "
        "limit (no point offering to expand something that isn't cut). Truncating with "
        "`trimEnd()` before adding the ellipsis avoids a dangling space before \"…\":",
        "write_file", expect=r"ok:", path="components/ExpandableText.tsx", content=EXPANDABLE_TEXT)
    ep.verify_green(
        "Written. Typecheck:")
    ep.final(
        "`components/ExpandableText.tsx` done: truncates at `maxChars` (default 180) with "
        "a \"read more\"/\"read less\" toggle — the button only renders when the text "
        "actually needs truncation. Client component (toggle state), typecheck green.")
    return ep


# ============================================================ L3 — investigação autônoma

STOCK_LEVEL_BUG = '''export function stockStatus(quantity: number): "in-stock" | "low" | "out" {
  if (quantity === 0) return "out";
  if (quantity < 5) return "low";
  return "in-stock";
}
'''


def l3_13(E):
    ep = E("L3", "l3-13-corrige-o-diagnostico-do-usuario",
           setup={"files": {"lib/stock.ts": STOCK_LEVEL_BUG}})
    ep.user("acho que o bug é que a função stockStatus não trata estoque negativo, deve ser isso que tá quebrando a página de produto")
    ep.act(
        "Vou verificar sua hipótese antes de aplicar a correção baseada nela — lendo o "
        "código real:",
        "read_file", expect=r"stockStatus", path="lib/stock.ts")
    ep.act(
        "Na verdade `stockStatus` está bem defensiva: `quantity === 0` cai em \"out\", e "
        "qualquer negativo cairia em `quantity < 5` → \"low\" (não trata como erro, mas "
        "também não quebra ou lança exceção). Não vejo como essa função quebraria a "
        "página. Confiro o typecheck do projeto todo, caso o problema esteja em outro "
        "lugar que essa função só reflete:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "Investiguei sua hipótese e ela não se sustenta: `stockStatus` já lida com "
        "estoque negativo sem quebrar (cai em \"low\", nunca lança erro) — não é essa "
        "função a causa. O typecheck do projeto também está limpo, então não há erro de "
        "tipo escondido em algum outro arquivo. Preciso de mais informação real pra achar "
        "a causa: qual é o erro exato que aparece (mensagem do console, ou o "
        "comportamento visual errado que você vê na página)? Sem isso, eu estaria "
        "consertando um problema que não existe.")
    return ep


def l3_14(E):
    ep = E("L3", "l3-14-funciona-na-minha-maquina", lang="en")
    ep.user("weird, it works fine on my machine but a teammate says the build fails for them. any idea?")
    ep.act(
        "\"Works on my machine\" almost always means an environment difference, not a code "
        "difference. Before speculating, let me reproduce the build myself in a clean "
        "run and see if it actually fails here too — that tells me whether it's the code "
        "or the machine:",
        "run_terminal", expect=r"\[exit 0\]", command="npm run build")
    ep.final(
        "It builds clean here too, exit 0 — so the code itself isn't broken; this points "
        "toward an environment difference, not a bug. Classic candidates worth having "
        "your teammate check, in order of likelihood: (1) uncommitted local files — "
        "something exists on your machine that never made it into a commit or is "
        "gitignored; (2) stale `node_modules` — ask them to delete it and `npm ci` fresh "
        "against the committed lockfile, since a mismatched lockfile is the single most "
        "common cause of this exact symptom; (3) a different Node version — worth "
        "comparing `node --version` between machines. I can't diagnose further without "
        "seeing their actual error output, but I'd bet on the lockfile before anything "
        "else.")
    return ep


CART_BADGE_MISNAMED_REQUEST = '''export function getCartCount(): number {
  return 0;
}
'''


def l3_15(E):
    ep = E("L3", "l3-15-le-antes-de-assumir-arquitetura",
           setup={"files": {"lib/cart.ts": CART_BADGE_MISNAMED_REQUEST}})
    ep.user("preciso que o contador do carrinho no header reflita o carrinho de verdade, hoje ele deve estar mockado")
    ep.act(
        "Antes de assumir COMO o carrinho real deveria funcionar (contexto? localStorage? "
        "API?), confiro o que já existe pra não reinventar uma arquitetura que talvez já "
        "esteja parcialmente decidida:",
        "read_file", expect=r"getCartCount", path="lib/cart.ts")
    ep.act(
        "Confirmado: `getCartCount` está mesmo mockada, sempre retorna 0, sem nenhuma "
        "pista de onde o carrinho real guardaria estado (nem localStorage, nem chamada de "
        "API, nem um Context declarado em algum lugar). Antes de eu inventar uma "
        "arquitetura de carrinho do zero — decisão grande demais pra tomar sozinho — "
        "confiro se existe algo relacionado no restante do projeto:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "Confirmei que `getCartCount` está mesmo mockada (sempre 0), mas não achei "
        "nenhuma peça de carrinho real no projeto — nem Context, nem chamada de API, nem "
        "persistência local. Isso significa que \"conectar ao carrinho de verdade\" não é "
        "uma troca pontual de função, é decidir uma arquitetura nova (Context? "
        "localStorage? API do backend?), e essa é uma decisão de produto que prefiro não "
        "tomar sozinho. Antes de eu implementar algo, me diz: o carrinho já existe em "
        "algum lugar (backend, outro repo) que eu devo consumir, ou é pra criar o estado "
        "do zero no frontend?")
    return ep


# ============================================================ L4 — estilo completo num edit

RATING_SUMMARY_POOR = '''export default function RatingSummary({ average, total }: { average: number; total: number }) {
  return (
    <div>
      <span>{average}</span>
      <span>({total} avaliações)</span>
    </div>
  );
}
'''

RATING_SUMMARY_GOOD = '''export default function RatingSummary({ average, total }: { average: number; total: number }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-2xl font-bold tracking-tight tabular-nums">{average.toFixed(1)}</span>
      <span className="text-sm text-zinc-500 dark:text-zinc-400">
        ({total} {total === 1 ? "avaliação" : "avaliações"})
      </span>
    </div>
  );
}
'''


def l4_13(E):
    ep = E("L4", "l4-13-rating-summary", setup={"files": {"components/RatingSummary.tsx": RATING_SUMMARY_POOR}})
    ep.user("o resumo de avaliação tá só os números crus sem formatação nenhuma, e acho que fica estranho no singular também. dá um trato")
    ep.act(
        "Vendo o estado atual:",
        "read_file", expect=r"RatingSummary", path="components/RatingSummary.tsx")
    ep.act(
        "Confirmado seu segundo ponto também: com `total=1` sairia \"(1 avaliações)\", "
        "gramaticalmente errado. 4 correções, um edit:\n"
        "1. o bug do plural: singular/plural condicional;\n"
        "2. `average` sem formatação pode sair com casas decimais inconsistentes "
        "(4 vs 4.33333) → `.toFixed(1)` fixa uma casa sempre;\n"
        "3. hierarquia: a média é a informação-herói → text-2xl font-bold, o total "
        "rebaixado ao lado;\n"
        "4. `tabular-nums` no número, útil se aparecer numa lista de produtos "
        "comparando ratings.\n"
        "Aplicando:",
        "write_file", expect=r"ok:", path="components/RatingSummary.tsx", content=RATING_SUMMARY_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "RatingSummary corrigido: o bug do singular/plural que você suspeitava era real "
        "(\"1 avaliações\" antes) e está corrigido, a média agora vem formatada com uma "
        "casa decimal fixa (`toFixed(1)`) e ganhou peso tipográfico como informação-herói, "
        "com o total rebaixado ao lado. Compilando limpo.")
    return ep


TIMESTAMP_BADGE_POOR = '''export default function TimestampBadge({ isoDate }: { isoDate: string }) {
  return <span>{isoDate}</span>;
}
'''

TIMESTAMP_BADGE_GOOD = '''function timeAgo(isoDate: string): string {
  const diffMs = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "agora mesmo";
  if (minutes < 60) return `há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `há ${hours}h`;
  const days = Math.floor(hours / 24);
  return `há ${days}d`;
}

export default function TimestampBadge({ isoDate }: { isoDate: string }) {
  return (
    <time
      dateTime={isoDate}
      title={new Date(isoDate).toLocaleString("pt-BR")}
      className="text-xs text-zinc-400 dark:text-zinc-500"
    >
      {timeAgo(isoDate)}
    </time>
  );
}
'''


def l4_14(E):
    ep = E("L4", "l4-14-timestamp-badge", setup={"files": {"components/TimestampBadge.tsx": TIMESTAMP_BADGE_POOR}})
    ep.user("o TimestampBadge mostra a data ISO crua tipo '2026-07-20T14:30:00Z', ninguém quer ler isso. conserta")
    ep.act(
        "Vendo o componente atual:",
        "read_file", expect=r"TimestampBadge", path="components/TimestampBadge.tsx")
    ep.act(
        "Confirmado — exibe a string ISO sem tratamento nenhum. 4 correções:\n"
        "1. o pedido central: texto relativo (\"há 5 min\", \"há 2h\", \"há 3d\") em vez "
        "da ISO crua;\n"
        "2. mas a data completa não deve DESAPARECER — só fica em `title`, pro hover "
        "nativo mostrar a data exata quando alguém precisar (informação relativa perde "
        "precisão de propósito, o `title` recupera isso sob demanda);\n"
        "3. elemento semântico `<time dateTime={isoDate}>` em vez de `<span>` — "
        "acessibilidade e SEO ganham a data máquina-legível junto com o texto humano;\n"
        "4. cor rebaixada (`zinc-400`/`zinc-500`) — timestamp é sempre informação "
        "secundária.\n"
        "Aplicando:",
        "write_file", expect=r"ok:", path="components/TimestampBadge.tsx", content=TIMESTAMP_BADGE_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "TimestampBadge corrigido: agora mostra tempo relativo (\"há 5 min\", \"há 2h\", "
        "\"há 3d\") em vez da ISO crua, mas a data completa não sumiu — fica no `title`, "
        "acessível via hover. Trocado `<span>` por `<time dateTime={isoDate}>` (semântica "
        "correta) e cor rebaixada, condizente com informação secundária. Compilando "
        "limpo.")
    return ep


SOCIAL_LINKS_POOR = '''export default function SocialLinks() {
  return (
    <div>
      <a href="https://twitter.com/example">Twitter</a>
      <a href="https://github.com/example">GitHub</a>
    </div>
  );
}
'''

SOCIAL_LINKS_GOOD = '''export default function SocialLinks() {
  const links = [
    { label: "Twitter", href: "https://twitter.com/example" },
    { label: "GitHub", href: "https://github.com/example" },
  ];
  return (
    <div className="flex items-center gap-4">
      {links.map((link) => (
        <a
          key={link.label}
          href={link.href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={link.label}
          className="text-zinc-500 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          {link.label}
        </a>
      ))}
    </div>
  );
}
'''


def l4_15(E):
    ep = E("L4", "l4-15-social-links-en", lang="en", setup={"files": {"components/SocialLinks.tsx": SOCIAL_LINKS_POOR}})
    ep.user("SocialLinks looks unstyled and I noticed the links don't open in a new tab, can you fix that and make it look decent?")
    ep.act(
        "Reading it first — the missing new-tab behavior you flagged is a real gap, plus "
        "there's a security issue that comes bundled with fixing it:",
        "read_file", expect=r"SocialLinks", path="components/SocialLinks.tsx")
    ep.act(
        "Full audit — five things, one rewrite:\n"
        "1. your ask: `target=\"_blank\"` to open in a new tab;\n"
        "2. the security catch that comes with #1: `target=\"_blank\"` without "
        "`rel=\"noopener noreferrer\"` lets the opened page access `window.opener` — a "
        "known vulnerability, always pair the two;\n"
        "3. no layout at all → flex row with gap;\n"
        "4. muted color with hover to full color (standard link treatment for icon/text "
        "row navigation, not underlined body-text style);\n"
        "5. no dark mode;\n"
        "Also added `aria-label` per link since a future icon-only version would need it — "
        "cheap to add now, matches the pattern used elsewhere in the project.\n"
        "Writing it:",
        "write_file", expect=r"ok:", path="components/SocialLinks.tsx", content=SOCIAL_LINKS_GOOD)
    ep.verify_green(
        "Rewritten. Typecheck:")
    ep.final(
        "Fixed what you asked plus a security detail that comes with it: links now open "
        "in a new tab via `target=\"_blank\"`, paired with `rel=\"noopener noreferrer\"` "
        "(required whenever you use `target=\"_blank\"` — otherwise the opened page can "
        "reach back into `window.opener`). Styled as a horizontal row with muted-to-full "
        "color hover and dark mode. Typecheck green.")
    return ep


# ============================================================ L5 — recuperação de tool call

def l5_14(E):
    ep = E("L5", "l5-14-path-aninhado-errado",
           setup={"files": {"components/PriceBox.tsx": "export default function PriceBox() { return null; }\n"}})
    ep.user("adiciona uma borda arredondada no PriceBox")
    ep.act(
        "Este projeto às vezes organiza componentes de base numa subpasta `ui/` — tento "
        "esse caminho primeiro:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/ui/PriceBox.tsx")
    ep.act(
        "Não está em `ui/` — neste caso o componente vive direto em `components/`. "
        "Tentando o caminho certo:",
        "read_file", expect=r"PriceBox", path="components/PriceBox.tsx")
    ep.act(
        "Achei. É um componente vazio (retorna `null`) — a mudança de borda não tem onde "
        "pegar ainda, então adiciono um wrapper mínimo com a classe pedida:",
        "edit_file", expect=r"ok:", path="components/PriceBox.tsx",
        old="export default function PriceBox() { return null; }",
        new='export default function PriceBox() {\n  return <div className="rounded-2xl border border-zinc-200 dark:border-zinc-800" />;\n}')
    ep.verify_green(
        "Wrapper adicionado. Typecheck:")
    ep.final(
        "Adicionei a borda arredondada — mas primeiro uma nota de processo: tentei "
        "`components/ui/PriceBox.tsx` (esse projeto às vezes usa essa subpasta), não "
        "existia, e achei em `components/PriceBox.tsx`. O componente estava vazio "
        "(retornava só `null`), então criei um `div` com `rounded-2xl border` — se ele "
        "deveria ter outro conteúdo, me avisa que eu ajusto o wrapper.")
    return ep


def l5_15(E):
    ep = E("L5", "l5-15-extensao-errada",
           setup={"files": {"components/PriceBox.tsx": "export default function PriceBox() { return null; }\n"}})
    ep.user("muda o PriceBox pra aceitar uma prop de título")
    ep.act(
        "Lendo o componente atual — assumindo a extensão .jsx por hábito, mas este "
        "projeto é TypeScript:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/PriceBox.jsx")
    ep.act(
        "Certo, extensão errada — projeto TS usa `.tsx`, não `.jsx`. Corrijo:",
        "read_file", expect=r"PriceBox", path="components/PriceBox.tsx")
    ep.act(
        "Componente vazio. Adiciono a prop de título tipada:",
        "edit_file", expect=r"ok:", path="components/PriceBox.tsx",
        old="export default function PriceBox() { return null; }",
        new='export default function PriceBox({ title }: { title: string }) {\n  return <p>{title}</p>;\n}')
    ep.verify_green(
        "Prop adicionada. Typecheck:")
    ep.final(
        "PriceBox agora aceita `title: string` e renderiza. Nota rápida: minha primeira "
        "tentativa de leitura assumiu `.jsx` por hábito — este projeto é TypeScript "
        "(`.tsx`), corrigi na segunda tentativa. O componente estava vazio antes; se o "
        "título deveria ter outro estilo além de um `<p>` simples, me avisa.")
    return ep


BUTTON_GROUP_STUB = "export default function ButtonGroup() { return null; }\n"


def l5_16(E):
    ep = E("L5", "l5-16-content-nao-string-en", lang="en",
           setup={"files": {"components/ButtonGroup.tsx": BUTTON_GROUP_STUB}})
    ep.user("stub out ButtonGroup so it renders a row with three placeholder labels: 'One', 'Two', 'Three'")
    ep.act(
        "Building the labels as a list feels natural — passing it straight through:",
        "write_file", expect=r"argumento 'content' deveria ser string",
        path="components/ButtonGroup.tsx",
        content=["One", "Two", "Three"])
    ep.act(
        "Right — `content` has to be the actual TSX SOURCE as a string, not a data "
        "structure; I can't hand the tool a list and expect it to be serialized into "
        "code. Writing the real file content:",
        "write_file", expect=r"ok:",
        path="components/ButtonGroup.tsx",
        content='''export default function ButtonGroup() {
  const labels = ["One", "Two", "Three"];
  return (
    <div className="flex gap-2">
      {labels.map((label) => (
        <button
          key={label}
          type="button"
          className="h-9 rounded-xl border border-zinc-300 px-3 text-sm transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          {label}
        </button>
      ))}
    </div>
  );
}
''')
    ep.verify_green(
        "Written for real this time. Typecheck:")
    ep.final(
        "ButtonGroup now renders three placeholder buttons (One/Two/Three) from a labels "
        "array mapped into buttons. Quick process note: my first attempt passed a plain "
        "list as `content` instead of actual source code text — the tool correctly "
        "rejected it (content must be a string of real TSX), and the retry wrote the "
        "actual file. Typecheck green.")
    return ep


# ============================================================ LC — conversa técnica

def lc_13(E):
    ep = E("LC", "lc-13-rest-vs-graphql")
    ep.user("Time discutindo se migra a API de REST pra GraphQL. Do ponto de vista de quem consome no frontend, vale a pena?")
    ep.final(
        "Do ponto de vista de consumo no frontend, minha resposta é: depende de UM "
        "sintoma específico que você consegue verificar hoje mesmo — overfetching/"
        "underfetching crônico.\n\n"
        "**Onde GraphQL realmente ajuda o frontend:** se hoje vocês fazem uma tela que "
        "precisa de dados de 3-4 endpoints REST diferentes (perfil + pedidos + "
        "notificações, por exemplo) e o frontend monta esses waterfalls de requisição "
        "manualmente, ou se um único endpoint REST devolve um objeto gigante do qual a "
        "tela só usa 3 campos — esses dois sintomas (underfetching e overfetching) são "
        "exatamente o que GraphQL resolve: uma query que pede só os campos que a tela "
        "usa, de várias fontes, numa viagem de rede só.\n\n"
        "**Onde é custo sem ganho proporcional:** se as telas do produto majoritariamente "
        "mapeiam 1-para-1 com endpoints REST simples (a tela de pedido busca `/pedidos/"
        "{id}` e usa quase tudo que vem), GraphQL não tem muito o que otimizar — vocês "
        "pagariam a complexidade de um schema, resolvers, e uma camada de cache no "
        "cliente (Apollo/urql) mais sofisticada que `fetch` simples, sem colher o "
        "benefício principal.\n\n"
        "**Custo que o time de frontend especificamente sente:** a curva de aprendizado "
        "de cache normalizado (Apollo Client cacheia por ID de objeto, não por URL como "
        "REST) confunde quem só conhece `fetch`/`useSWR`; e depurar uma query GraphQL "
        "malformada às vezes é menos direto que ver um 404/500 de REST no Network tab.\n\n"
        "Pergunta de verificação: nas últimas telas complexas que vocês construíram, "
        "quantas chamadas de rede sequenciais o frontend precisou fazer pra montar UMA "
        "tela? Se a resposta for \"3+\", GraphQL provavelmente compensa. Se for \"1-2\", "
        "REST já está fazendo o trabalho e a migração seria custo sem sintoma real por "
        "trás.")
    return ep


def lc_14(E):
    ep = E("LC", "lc-14-bem-em-tailwind-en", lang="en")
    ep.user("does a naming methodology like BEM still matter now that we're all-in on Tailwind, or is that a solved problem?")
    ep.final(
        "It's mostly solved for the exact thing BEM was invented for, but not entirely — "
        "there's a residual case worth naming explicitly.\n\n"
        "**What BEM solved that Tailwind makes moot:** BEM's whole point was giving CSS "
        "class NAMES enough structure to avoid specificity wars and unintended cascade "
        "(`.card__title--featured` tells you exactly what it modifies and prevents "
        "accidental global leakage). With Tailwind, you're not naming abstractions at "
        "all — you're composing utility classes inline, so there's no cascade to manage "
        "and no naming scheme needed for 90% of components. That problem really is gone.\n\n"
        "**Where a naming-adjacent problem still exists:** the moment you extract a "
        "REUSABLE custom class via `@apply` or a CSS variable-driven design token (which "
        "most real projects eventually do for things like brand colors or a repeated "
        "complex gradient), you're back to naming something — and BEM's discipline "
        "(block/element/modifier, not \"thing2\" or \"card-new\") is still genuinely "
        "useful there. It's just applied to a much smaller surface area than before.\n\n"
        "**The practical takeaway:** you don't need BEM as your primary methodology "
        "anymore — Tailwind's utility-first approach replaces the 90% case. But when you "
        "do name a handful of custom classes or CSS custom properties, borrowing BEM's "
        "STRUCTURE (describe the block and its role, not an arbitrary label) is still the "
        "best default, even without adopting the full methodology or its double-underscore "
        "syntax. Think of it as BEM's principles surviving BEM's ceremony.")
    return ep


def lc_15(E):
    ep = E("LC", "lc-15-ui-kit-vs-custom")
    ep.user("MVP começando do zero. Vale montar tudo com componente próprio, ou parte de um kit pronto tipo shadcn/MUI pra ganhar velocidade?")
    ep.final(
        "Pra MVP, minha recomendação é kit pronto — mas com uma ressalva importante sobre "
        "QUAL tipo de kit, porque nem todos têm a mesma saída de emergência depois.\n\n"
        "**Por que kit pronto pra MVP:** a métrica que importa num MVP é velocidade até "
        "validar a hipótese de produto, não elegância de arquitetura de componentes. "
        "Escrever Button/Modal/Dropdown/Select do zero com acessibilidade decente "
        "(focus trap, aria correto, navegação por teclado) é trabalho genuinamente "
        "difícil e fácil de fazer mal — um kit maduro já resolveu isso e testou contra "
        "casos extremos que você nem pensaria em testar num MVP.\n\n"
        "**A ressalva que separa uma boa de uma má escolha:** existe uma diferença "
        "grande entre kits que te dão CÓDIGO (shadcn/ui é o exemplo clássico — ele copia "
        "os componentes pro seu projeto, viram seu código, customizáveis livremente) e "
        "kits que te dão uma BIBLIOTECA fechada (MUI clássico, onde você importa um "
        "componente compilado e customiza via props/tema do sistema deles). O primeiro "
        "tipo tem saída de emergência: se o produto validar e vocês precisarem de um "
        "design totalmente diferente, vocês já possuem o código e editam livremente. O "
        "segundo tipo prende vocês ao sistema de tema da lib — reskin profundo "
        "geralmente significa reescrever, não ajustar.\n\n"
        "Então a recomendação afiada: pra MVP, um kit do tipo \"copia o código pro seu "
        "projeto\" (shadcn/ui e similares) dá a velocidade que você quer AGORA sem "
        "hipotecar a flexibilidade que você vai querer DEPOIS, se o produto vingar e "
        "precisar de identidade visual própria.")
    return ep


EPISODES = [
    l1_17, l1_18, l1_19, l1_20,
    l2_15, l2_16, l2_17,
    l3_13, l3_14, l3_15,
    l4_13, l4_14, l4_15,
    l5_14, l5_15, l5_16,
    lc_13, lc_14, lc_15,
]
