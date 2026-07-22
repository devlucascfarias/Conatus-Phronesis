# -*- coding: utf-8 -*-
"""Batch e007 — 19 episódios. Códigos/comportamentos confirmados por execução real ANTES
da CoT: TS7053 (index signature ausente), TS18047 (possibly null, DOM query), destructuring
de tupla trocado (LOGIC bug, tsc passa limpo — segunda instância desse padrão importante).
npm run com script inexistente e edit com espaçamento divergente confirmados via probe.
"""

# ============================================================ L1 — ciclo completo

PRICES_LIB_BROKEN = '''const PRICE_BY_PLAN = {
  basic: 29.9,
  pro: 59.9,
};

export function priceOf(plan: string): number {
  return PRICE_BY_PLAN[plan];
}
'''


def l1_24(E):
    ep = E("L1", "l1-24-index-signature-ausente", setup={"files": {"lib/prices.ts": PRICES_LIB_BROKEN}})
    ep.user("lib/prices.ts não compila, o objeto de preços por plano tá certinho mas a função que busca dá erro")
    ep.act(
        "Confiro o erro exato:",
        "run_terminal", expect=r"error TS7053", command="npx tsc --noEmit")
    ep.act(
        "TS7053: o TypeScript infere `PRICE_BY_PLAN` como um tipo com só as chaves "
        "literais `basic`/`pro`, e `priceOf` tenta indexar com `plan: string` (qualquer "
        "string, não um dos dois literais) — não há garantia de que a chave exista, "
        "então o TS recusa. Duas soluções possíveis: tipar `plan` como o literal exato "
        "(`\"basic\" | \"pro\"`, mais seguro) ou dar uma assinatura de índice ao objeto "
        "(mais permissivo, mas aceita qualquer string em runtime). Como a função é uma "
        "busca por plano — universo pequeno e conhecido — o tipo literal é a escolha "
        "mais segura:",
        "edit_file", expect=r"ok:", path="lib/prices.ts",
        old="export function priceOf(plan: string): number {",
        new='export function priceOf(plan: "basic" | "pro"): number {')
    ep.verify_green(
        "Tipo restringido ao universo real de planos. Typecheck:")
    ep.final(
        "TS7053: `plan: string` era genérico demais pra indexar um objeto com só duas "
        "chaves conhecidas. Troquei a assinatura pra `plan: \"basic\" | \"pro\"` — mais "
        "seguro que dar uma assinatura de índice ao objeto, porque agora o compilador "
        "recusa qualquer chamada com plano que não exista, em vez de aceitar qualquer "
        "string e devolver `undefined` em runtime silenciosamente. Typecheck verde.")
    return ep


PAIR_LIB_LOGIC_BUG = '''function minMax(values: number[]): [number, number] {
  return [Math.min(...values), Math.max(...values)];
}

export function rangeLabel(values: number[]): string {
  const [max, min] = minMax(values);
  return `de ${min} ate ${max}`;
}
'''


def l1_25(E):
    ep = E("L1", "l1-25-destructuring-trocado", setup={"files": {"lib/pair.ts": PAIR_LIB_LOGIC_BUG}})
    ep.user("o rangeLabel tá saindo invertido, tipo 'de 100 ate 10' em vez de 'de 10 ate 100'. o typecheck passa limpo")
    ep.act(
        "Se o typecheck passa, é bug de lógica — o compilador não vai me ajudar aqui, "
        "preciso ler o código com atenção:",
        "read_file", expect=r"minMax", path="lib/pair.ts")
    ep.act(
        "Achei: `minMax` devolve a tupla na ordem `[min, max]` (primeiro o menor, depois "
        "o maior — o próprio nome da função e da implementação deixam isso claro). Mas "
        "`rangeLabel` desestrutura como `const [max, min] = minMax(values)` — ordem "
        "trocada. Como os dois são `number`, o TypeScript não tem como saber que você "
        "quis dizer o oposto do que escreveu; ele só vê dois números sendo atribuídos a "
        "duas variáveis `number`, sintaticamente válido. Corrijo a ordem da "
        "desestruturação pra bater com o que a função de fato devolve:",
        "edit_file", expect=r"ok:", path="lib/pair.ts",
        old="const [max, min] = minMax(values);", new="const [min, max] = minMax(values);")
    ep.verify_green(
        "Ordem corrigida. Confirmo que a sintaxe segue válida (o tsc não pegaria esse "
        "bug de qualquer forma, mas garante que nada mais quebrou):")
    ep.final(
        "Era troca de ordem na desestruturação: `minMax` devolve `[min, max]`, mas "
        "`rangeLabel` lia como `[max, min]` — como os dois são `number`, o TypeScript "
        "nunca acusaria isso, é puramente lógico. Corrigido pra `const [min, max] = "
        "minMax(values)`. Regra de bolso: ao desestruturar uma tupla, o NOME da "
        "variável não muda a posição que ela recebe — sempre confira a ordem real do "
        "retorno, não confie no nome que você deu à variável.")
    return ep


DOM_HELPERS_BROKEN = '''export function getHeaderHeight(): number {
  const header = document.querySelector("header");
  return header.offsetHeight;
}
'''

HEADER_PAGE = '''"use client";

import { useEffect } from "react";
import { getHeaderHeight } from "@/lib/dom-helpers";

export default function LandingPage() {
  useEffect(() => {
    console.log(getHeaderHeight());
  }, []);
  return (
    <>
      <header className="h-16 border-b border-zinc-200 dark:border-zinc-800" />
      <main className="p-4">Conteúdo</main>
    </>
  );
}
'''


def l1_26(E):
    ep = E("L1", "l1-26-possibly-null-dom", setup={"files": {
        "lib/dom-helpers.ts": DOM_HELPERS_BROKEN,
        "app/page.tsx": HEADER_PAGE,
    }})
    ep.user("lib/dom-helpers.ts não compila, é só um querySelector simples")
    ep.act(
        "\"Simples\" e ainda assim o compilador reclama — vamos ver o motivo exato:",
        "run_terminal", expect=r"error TS18047", command="npx tsc --noEmit")
    ep.act(
        "TS18047: `document.querySelector` sempre devolve `Element | null` — o "
        "TypeScript não tem como garantir que o seletor \"header\" vai encontrar algo "
        "no DOM (pode não existir ainda, pode ter sido removido). Acessar "
        "`.offsetHeight` direto ignora esse `null`. Trato o caso de ausência em vez de "
        "assumir que sempre existe:",
        "edit_file", expect=r"ok:", path="lib/dom-helpers.ts",
        old='  const header = document.querySelector("header");\n  return header.offsetHeight;',
        new=('  const header = document.querySelector("header");\n'
             '  return header ? header.offsetHeight : 0;'))
    ep.verify_green(
        "Caso nulo tratado com fallback de 0. Typecheck:")
    ep.final(
        "TS18047: `querySelector` sempre pode devolver `null` (o TypeScript modela isso "
        "corretamente, mesmo que na prática o `<header>` exista na página) — acessar "
        "`.offsetHeight` sem checar quebraria em runtime se o seletor não encontrasse "
        "nada. Adicionei o fallback `header ? header.offsetHeight : 0`. Typecheck verde. "
        "Isso não é burocracia do TS: se algum dia o header virar condicional na página, "
        "essa função já está protegida.")
    return ep


# ============================================================ L2 — entrega verificada

LOADING_PLACEHOLDER = '''export default function LoadingPlaceholder() {
  return (
    <div className="animate-pulse rounded-2xl border border-zinc-200 p-6 dark:border-zinc-800">
      <div className="h-4 w-1/3 rounded bg-zinc-200 dark:bg-zinc-800" />
      <div className="mt-3 h-3 w-full rounded bg-zinc-200 dark:bg-zinc-800" />
      <div className="mt-2 h-3 w-2/3 rounded bg-zinc-200 dark:bg-zinc-800" />
    </div>
  );
}
'''


def l2_22(E):
    ep = E("L2", "l2-22-loading-placeholder")
    ep.user("cria um placeholder de carregamento (tipo skeleton) pra um card genérico enquanto os dados não chegam. components/LoadingPlaceholder.tsx")
    ep.act(
        "Puramente visual, sem estado, sem tool — server component. `animate-pulse` do "
        "Tailwind já dá a animação de \"respirando\"; a estrutura interna (título mais "
        "largo, duas linhas de corpo com larguras diferentes) imita a assimetria de "
        "conteúdo real — um skeleton com todas as barras do mesmo tamanho lê como "
        "artificial demais:",
        "write_file", expect=r"ok:", path="components/LoadingPlaceholder.tsx", content=LOADING_PLACEHOLDER)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/LoadingPlaceholder.tsx` pronto: card com bordas no padrão do "
        "projeto, `animate-pulse` e três barras de largura variável (título + duas "
        "linhas de corpo) pra imitar a assimetria de conteúdo real em vez de barras "
        "uniformes. Server component, sem estado. Typecheck verde.")
    return ep


FORM_FIELD_ERROR = '''type FormFieldErrorProps = {
  message?: string;
  id: string;
};

export default function FormFieldError({ message, id }: FormFieldErrorProps) {
  if (!message) return null;

  return (
    <p id={id} role="alert" className="mt-1 text-sm text-rose-600 dark:text-rose-400">
      {message}
    </p>
  );
}
'''


def l2_23(E):
    ep = E("L2", "l2-23-form-field-error")
    ep.user("cria um componente pra mostrar erro de validação embaixo de um campo de formulário. components/FormFieldError.tsx, some se não tiver erro")
    ep.act(
        "Puramente condicional, sem estado — server component. Detalhe de acessibilidade "
        "que faz diferença de verdade aqui: o `id` recebido como prop serve pra o input "
        "referenciar via `aria-describedby={id}` (não implementado aqui, é "
        "responsabilidade do input consumidor, mas o componente já expõe o `id` certo "
        "pra isso funcionar) — e `role=\"alert\"` faz leitor de tela anunciar o erro "
        "assim que aparece, sem precisar de foco. `message` opcional some o componente "
        "inteiro quando não há erro, em vez de renderizar um espaço vazio:",
        "write_file", expect=r"ok:", path="components/FormFieldError.tsx", content=FORM_FIELD_ERROR)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/FormFieldError.tsx` pronto: recebe `message` opcional (não "
        "renderiza nada se ausente) e `id` (pro input pai referenciar via "
        "`aria-describedby`, associando o erro ao campo pra leitor de tela). "
        "`role=\"alert\"` anuncia o erro sem exigir foco. Server component, typecheck "
        "verde.")
    return ep


PRICE_RANGE_SLIDER = '''"use client";

import { useState } from "react";

type PriceRangeSliderProps = {
  min: number;
  max: number;
  onChange: (range: [number, number]) => void;
};

export default function PriceRangeSlider({ min, max, onChange }: PriceRangeSliderProps) {
  const [low, setLow] = useState(min);
  const [high, setHigh] = useState(max);

  function updateLow(value: number) {
    const clamped = Math.min(value, high);
    setLow(clamped);
    onChange([clamped, high]);
  }

  function updateHigh(value: number) {
    const clamped = Math.max(value, low);
    setHigh(clamped);
    onChange([low, clamped]);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium tabular-nums">R$ {low}</span>
        <span className="text-zinc-500 dark:text-zinc-400">até</span>
        <span className="font-medium tabular-nums">R$ {high}</span>
      </div>
      <div className="flex gap-2">
        <input
          type="range"
          min={min}
          max={max}
          value={low}
          onChange={(e) => updateLow(Number(e.target.value))}
          aria-label="Preço mínimo"
          className="flex-1 accent-zinc-900 dark:accent-zinc-100"
        />
        <input
          type="range"
          min={min}
          max={max}
          value={high}
          onChange={(e) => updateHigh(Number(e.target.value))}
          aria-label="Preço máximo"
          className="flex-1 accent-zinc-900 dark:accent-zinc-100"
        />
      </div>
    </div>
  );
}
'''


def l2_24(E):
    ep = E("L2", "l2-24-price-range-slider")
    ep.user("preciso de um filtro de faixa de preço com dois sliders (mínimo e máximo). components/PriceRangeSlider.tsx")
    ep.act(
        "Dois inputs range controlados — client component. O detalhe que evita bug "
        "clássico de faixa dupla: sem clamping, o slider de mínimo pode ultrapassar o "
        "máximo (e vice-versa), gerando uma faixa invertida sem sentido tipo \"de R$ 80 "
        "até R$ 20\". Cada `update` limita contra o valor do outro slider "
        "(`Math.min(value, high)` / `Math.max(value, low)`), então os dois nunca se "
        "cruzam. `accent-color` via classe do Tailwind estiliza o range nativo sem "
        "precisar reconstruir o input do zero, e cada slider tem `aria-label` distinto "
        "(mín/máx) já que visualmente são dois controles parecidos:",
        "write_file", expect=r"ok:", path="components/PriceRangeSlider.tsx", content=PRICE_RANGE_SLIDER)
    ep.verify_green(
        "Escrito. Typecheck:")
    ep.final(
        "`components/PriceRangeSlider.tsx` pronto: dois sliders nativos com clamping "
        "mútuo — o mínimo nunca ultrapassa o máximo e vice-versa, evitando faixa "
        "invertida. `onChange` devolve a tupla `[low, high]` sempre que qualquer um dos "
        "dois muda, cada input com `aria-label` distinto. Client component (estado dos "
        "dois valores), typecheck verde.")
    return ep


LANGUAGE_SWITCHER = '''"use client";

const LANGUAGES = [
  { code: "pt-BR", label: "Português" },
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
];

export default function LanguageSwitcher({
  current,
  onChange,
}: {
  current: string;
  onChange: (code: string) => void;
}) {
  return (
    <label className="inline-flex items-center gap-2 text-sm">
      <span className="sr-only">Language</span>
      <select
        value={current}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 rounded-xl border border-zinc-300 bg-white px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-900"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
    </label>
  );
}
'''


def l2_25(E):
    ep = E("L2", "l2-25-language-switcher-en", lang="en")
    ep.user("need a simple language switcher dropdown, three languages for now. components/LanguageSwitcher.tsx")
    ep.act(
        "Controlled select with onChange — client component. Using a native `<select>` "
        "rather than a custom dropdown here: for a short, well-known list of options "
        "(languages), the native element gives free keyboard navigation and mobile "
        "picker behavior that a custom-built dropdown would have to reimplement. Wrapped "
        "in a `<label>` with `sr-only` text since the select has no visible label "
        "otherwise — screen readers still need to know what this control does:",
        "write_file", expect=r"ok:", path="components/LanguageSwitcher.tsx", content=LANGUAGE_SWITCHER)
    ep.verify_green(
        "Written. Typecheck:")
    ep.final(
        "`components/LanguageSwitcher.tsx` done: native `<select>` (free a11y and mobile "
        "behavior for a short known list) wrapped in a `sr-only`-labeled `<label>`, "
        "controlled via `current`/`onChange` props. Client component, typecheck green.")
    return ep


# ============================================================ L3 — investigação autônoma

TOTALS_BUG = '''export function sumCart(prices: number[]): number {
  let total = 0;
  for (let i = 1; i < prices.length; i++) {
    total += prices[i];
  }
  return total;
}
'''


def l3_19(E):
    ep = E("L3", "l3-19-le-linha-exata-do-stack",
           setup={"files": {"lib/cart-math.ts": TOTALS_BUG}})
    ep.user("erro no console: \"o total do carrinho não bate\" — o time de QA mandou o print e disse que é em lib/cart-math.ts, função sumCart")
    ep.act(
        "Localização exata em mãos — leio a função direto em vez de adivinhar o que "
        "pode estar errado:",
        "read_file", expect=r"sumCart", path="lib/cart-math.ts")
    ep.act(
        "Achei: o loop começa em `i = 1`, não `i = 0` — o primeiro item do array "
        "(`prices[0]`) nunca entra na soma. Com um carrinho de 3 itens, o total sempre "
        "vem faltando exatamente o valor do primeiro. Corrijo o índice inicial:",
        "edit_file", expect=r"ok:", path="lib/cart-math.ts",
        old="for (let i = 1; i < prices.length; i++) {",
        new="for (let i = 0; i < prices.length; i++) {")
    ep.verify_green(
        "Índice corrigido. Typecheck (não pegaria esse bug de lógica, mas confirma que "
        "nada mais quebrou):")
    ep.final(
        "Achado: o loop em `sumCart` começava em `i = 1` em vez de `i = 0`, então o "
        "primeiro item do carrinho nunca era somado — clássico off-by-one. Corrigido "
        "pra começar em 0. Isso é exatamente o tipo de bug que o typecheck nunca "
        "pegaria (índice válido, tipo certo, só a lógica errada), então avisa o time de "
        "QA que vale testar de novo com carrinhos de tamanhos diferentes pra garantir "
        "que não sobrou outro caso de borda.")
    return ep


def l3_20(E):
    ep = E("L3", "l3-20-checa-mais-provavel-primeiro", lang="en")
    ep.user("checkout page throws an error on load, could be the CartSummary, the PaymentForm, or the ShippingCalculator — not sure which")
    ep.act(
        "Three candidates, but I'll check the most likely first rather than reading all "
        "three blind: an error \"on load\" (not on interaction) usually points to "
        "something that runs immediately — CartSummary is typically the first thing "
        "rendered and often does data transformation on mount, so I start there:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/CartSummary.tsx")
    ep.act(
        "Doesn't exist in this project yet — ruling it out immediately narrows to two. "
        "Checking PaymentForm next, since forms often have synchronous setup logic that "
        "runs on mount too:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/PaymentForm.tsx")
    ep.final(
        "Neither `CartSummary.tsx` nor `PaymentForm.tsx` exists in this project — so by "
        "elimination, if the error is real, it's most likely in `ShippingCalculator` (the "
        "third candidate), or the component has a different file name than what you "
        "gave me. Before I guess at a third file name, can you confirm the actual file "
        "path, or paste the stack trace? That'll point at the exact line instead of me "
        "continuing to guess names one by one.")
    return ep


# ============================================================ L4 — estilo completo num edit

TAG_LIST_POOR = '''export default function TagList({ tags }: { tags: string[] }) {
  return (
    <div>
      {tags.map((t) => (
        <span key={t}>{t}</span>
      ))}
    </div>
  );
}
'''

TAG_LIST_GOOD = '''export default function TagList({ tags }: { tags: string[] }) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {tags.map((t) => (
        <span
          key={t}
          className="shrink-0 rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
        >
          {t}
        </span>
      ))}
    </div>
  );
}
'''


def l4_19(E):
    ep = E("L4", "l4-19-tag-list", setup={"files": {"components/TagList.tsx": TAG_LIST_POOR}})
    ep.user("a lista de tags quebra linha e fica feia quando tem muitas — queria que rolasse horizontalmente em vez disso. e também não tem estilo nenhum")
    ep.act(
        "Vendo o atual:",
        "read_file", expect=r"TagList", path="components/TagList.tsx")
    ep.act(
        "Confirmado — `<div>` sem `flex` faz as tags empilharem uma embaixo da outra "
        "(bloco), não quebrar linha lado a lado como você descreveu, mas o efeito visual "
        "ruim é o mesmo motivo. 4 correções, um edit:\n"
        "1. seu pedido central: `flex` (lado a lado) + `overflow-x-auto` (rola em vez de "
        "quebrar) + `pb-1` (espaço pra barra de scroll não colar no conteúdo);\n"
        "2. `shrink-0` em cada tag — sem isso, o flex tentaria espremer as tags pra "
        "caber, item errado pra um container que já rola;\n"
        "3. formato pill (rounded-full) no lugar de texto solto sem estilo;\n"
        "4. dark mode.\n"
        "Aplicando:",
        "write_file", expect=r"ok:", path="components/TagList.tsx", content=TAG_LIST_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "TagList corrigido: agora é uma fileira horizontal que rola (`flex` + "
        "`overflow-x-auto`) em vez de empilhar, cada tag com `shrink-0` pra não ser "
        "espremida, formato pill e dark mode. Compilando limpo.")
    return ep


EMPTY_CART_POOR = '''export default function EmptyCart() {
  return <p>Carrinho vazio</p>;
}
'''

EMPTY_CART_GOOD = '''import Link from "next/link";

export default function EmptyCart() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-zinc-300 px-6 py-16 text-center dark:border-zinc-700">
      <svg
        viewBox="0 0 24 24"
        className="h-10 w-10 text-zinc-400 dark:text-zinc-600"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        aria-hidden="true"
      >
        <path d="M3 3h2l.4 2M7 13h10l3.6-8H5.4M7 13L5.4 5M7 13l-2.3 4.6A1 1 0 005.6 19H17M17 13v6M9 21a1 1 0 100-2 1 1 0 000 2zM18 21a1 1 0 100-2 1 1 0 000 2z" />
      </svg>
      <p className="text-base font-medium">Seu carrinho está vazio</p>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">
        Adicione produtos pra ver eles aqui.
      </p>
      <Link
        href="/"
        className="mt-2 text-sm font-medium text-zinc-900 underline-offset-4 transition-colors hover:underline dark:text-zinc-100"
      >
        Continuar comprando
      </Link>
    </div>
  );
}
'''


def l4_20(E):
    ep = E("L4", "l4-20-empty-cart", setup={"files": {"components/EmptyCart.tsx": EMPTY_CART_POOR}})
    ep.user("o estado de carrinho vazio é só um texto solto, sem nada. melhora isso, é uma tela que todo mundo vê em algum momento")
    ep.act(
        "Concordo com a prioridade — estado vazio é visto por 100% dos usuários novos "
        "em algum momento, vale o cuidado. Vendo o atual:",
        "read_file", expect=r"EmptyCart", path="components/EmptyCart.tsx")
    ep.act(
        "5 correções pra virar uma tela de verdade:\n"
        "1. superfície de estado vazio (borda tracejada, bastante padding vertical) "
        "sinaliza \"isso é intencional, não é um bug de carregamento\";\n"
        "2. ícone de carrinho em aria-hidden — reforço visual sem competir com o texto;\n"
        "3. hierarquia: mensagem principal em peso maior, texto de apoio rebaixado;\n"
        "4. o elemento mais importante que faltava: um CAMINHO de saída — link "
        "\"Continuar comprando\" de volta pra home. Estado vazio sem ação é beco sem "
        "saída pro usuário;\n"
        "5. dark mode em tudo.\n"
        "Reescrevendo:",
        "write_file", expect=r"ok:", path="components/EmptyCart.tsx", content=EMPTY_CART_GOOD)
    ep.verify_green(
        "Reescrito. Typecheck:")
    ep.final(
        "EmptyCart virou uma tela de verdade: superfície de estado vazio (borda "
        "tracejada), ícone de carrinho, hierarquia entre mensagem principal e texto de "
        "apoio, e — o mais importante — um link \"Continuar comprando\" de volta pra "
        "home, que faltava completamente (sem isso era beco sem saída). Dark mode "
        "completo. Compilando limpo.")
    return ep


FOOTER_LINKS_POOR = '''export default function FooterLinks() {
  return (
    <footer>
      <a href="/termos">Termos</a>
      <a href="/privacidade">Privacidade</a>
      <a href="/contato">Contato</a>
    </footer>
  );
}
'''

FOOTER_LINKS_GOOD = '''import Link from "next/link";

const links = [
  { label: "Termos", href: "/termos" },
  { label: "Privacidade", href: "/privacidade" },
  { label: "Contato", href: "/contato" },
];

export default function FooterLinks() {
  return (
    <footer className="border-t border-zinc-200 py-6 dark:border-zinc-800">
      <nav aria-label="Links institucionais" className="mx-auto flex max-w-6xl flex-wrap justify-center gap-x-6 gap-y-2 px-4 text-sm">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="text-zinc-500 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </footer>
  );
}
'''


def l4_21(E):
    ep = E("L4", "l4-21-footer-links-en", lang="en", setup={"files": {"components/FooterLinks.tsx": FOOTER_LINKS_POOR}})
    ep.user("footer links are just plain <a> tags stacked with no styling or spacing, and I don't think they use Next's routing properly")
    ep.act(
        "Reading it — you're right about the routing issue, plain `<a>` tags cause a "
        "full page reload instead of client-side navigation:",
        "read_file", expect=r"FooterLinks", path="components/FooterLinks.tsx")
    ep.act(
        "Full fix — five things:\n"
        "1. your routing catch: `<a href>` → Next's `<Link href>`, restoring "
        "client-side navigation instead of full reloads;\n"
        "2. no layout at all → horizontal row with wrapping (`flex-wrap`) so it "
        "degrades gracefully on narrow screens instead of overflowing;\n"
        "3. no visual separation from page content above → `border-t` + vertical "
        "padding;\n"
        "4. muted-to-full-color hover, standard treatment for this kind of secondary "
        "nav;\n"
        "5. wrapped in `<nav aria-label=\"...\">` — a footer with multiple links is "
        "navigation, and the label distinguishes it from the page's primary nav for "
        "screen reader users.\n"
        "Rewriting:",
        "write_file", expect=r"ok:", path="components/FooterLinks.tsx", content=FOOTER_LINKS_GOOD)
    ep.verify_green(
        "Rewritten. Typecheck:")
    ep.final(
        "Fixed the routing bug you flagged (`<a>` → `<Link>`, restoring client-side "
        "navigation) plus styling: horizontal row that wraps on narrow screens, "
        "top border separating it from page content, muted-to-full hover, and wrapped "
        "in a labeled `<nav>` so screen readers distinguish it from primary navigation. "
        "Typecheck green.")
    return ep


# ============================================================ L5 — recuperação de tool call

def l5_20(E):
    ep = E("L5", "l5-20-npm-script-errado")
    ep.user("roda o build do projeto pra ver se compila")
    ep.act(
        "Rodando o script de build:",
        "run_terminal", expect=r"Missing script", command="npm run biuld")
    ep.act(
        "Typo meu: `biuld` não existe. O script certo, conforme o package.json do "
        "template, é `build`:",
        "run_terminal", expect=r"\[exit 0\]", command="npm run build")
    ep.final(
        "Build passou limpo (exit 0). Nota rápida: minha primeira tentativa teve um "
        "typo (`npm run biuld`), corrigido pra `npm run build` na segunda.")
    return ep


TAG_CHIP_STUB = 'export default function TagChip({ label }: { label: string }) {\n  return <span className="text-xs">{label}</span>;\n}\n'


def l5_21(E):
    ep = E("L5", "l5-21-old-com-espaco-extra", setup={"files": {"components/TagChip.tsx": TAG_CHIP_STUB}})
    ep.user("aumenta o texto do TagChip de text-xs pra text-sm")
    ep.act(
        "Editando a classe de tamanho:",
        "edit_file", expect=r"não encontrado",
        path="components/TagChip.tsx",
        old='className="text-xs" >{label}', new='className="text-sm">{label}')
    ep.act(
        "Não casou — assumi um espaço antes do `>` que não existe no arquivo real. Em "
        "vez de arriscar outra suposição de formatação, releio o arquivo e ancoro no "
        "texto exato:",
        "read_file", expect=r"text-xs", path="components/TagChip.tsx")
    ep.act(
        "Confirmado, sem espaço extra. Reenviando o edit ancorado no texto real:",
        "edit_file", expect=r"ok:",
        path="components/TagChip.tsx",
        old='className="text-xs">{label}', new='className="text-sm">{label}')
    ep.verify_green(
        "Classe atualizada. Typecheck:")
    ep.final(
        "TagChip com o texto aumentado (`text-xs` → `text-sm`). Nota de processo: meu "
        "primeiro edit assumiu um espaço antes do `>` que não existia de verdade no "
        "arquivo — reli e ancorei a segunda tentativa no texto exato em vez de chutar "
        "de novo. Typecheck verde.")
    return ep


def l5_22(E):
    ep = E("L5", "l5-22-comando-composto-bloqueado-en", lang="en")
    ep.user("clean up build artifacts and rebuild from scratch")
    ep.act(
        "Trying the clean step first:",
        "run_terminal", expect=r"não permitido", command="rm -rf .next && npm run build")
    ep.act(
        "`rm` isn't on this terminal's allowlist — but a clean rebuild doesn't strictly "
        "need it. Next's build already overwrites `.next` on every run, so a plain "
        "rebuild gets me most of the way there without deleting anything first:",
        "run_terminal", expect=r"\[exit 0\]", command="npm run build")
    ep.final(
        "Rebuilt successfully (exit 0). Couldn't run the `rm -rf .next` step — `rm` "
        "isn't in this terminal's allowed commands — but it turned out unnecessary: "
        "`next build` already regenerates `.next` fresh on every run, it doesn't reuse "
        "stale output from a previous build. If you specifically need the directory "
        "physically deleted first (e.g. to reclaim disk space), that's a step you'd run "
        "locally — `rm -rf .next` on your machine before `npm run build`.")
    return ep


# ============================================================ LC — conversa técnica

def lc_19(E):
    ep = E("LC", "lc-19-i18n-estrategia")
    ep.user("app vai internacionalizar (pt-BR, en, es). É melhor usar uma lib tipo next-intl, ou fazer um dicionário próprio simples?")
    ep.final(
        "Pra três idiomas com plano de crescer, eu iria de `next-intl` — mas vale "
        "entender exatamente qual problema uma lib resolve que um dicionário caseiro "
        "não resolve, porque não é só \"trocar texto\".\n\n"
        "**O que um dicionário próprio resolve bem:** troca de string simples "
        "(`t('welcome')` → \"Bem-vindo\"/\"Welcome\"/\"Bienvenido\") é trivial de "
        "implementar do zero, e pra um app pequeno com pouco texto isso realmente não "
        "justifica dependência nova.\n\n"
        "**Onde isso quebra rápido, e uma lib madura já resolveu:** pluralização "
        "(\"1 item\" vs \"2 itens\" — regras de plural MUDAM por idioma, o inglês tem 2 "
        "formas, o português também mas com exceções diferentes, outros idiomas têm "
        "3-6 formas); formatação de número/moeda/data por locale (R$ 1.234,56 vs "
        "$1,234.56 é mais que trocar o símbolo, é trocar separador decimal e de "
        "milhar); interpolação segura de variável dentro de string traduzida sem "
        "quebrar HTML; e — a mais cara de reinventar — roteamento por idioma "
        "(`/en/produtos` vs `/produtos`) integrado ao App Router, que o `next-intl` já "
        "resolve nativamente com middleware pronto.\n\n"
        "**Custo real do next-intl:** curva de aprendizado pequena (é razoavelmente "
        "direto) e mais uma dependência — mas comparado ao custo de reimplementar "
        "pluralização e formatação de locale corretamente (é MAIS difícil do que "
        "parece; regras de plural têm exceção em quase todo idioma), o kit pronto sai "
        "mais barato mesmo cedo.\n\n"
        "Sinal de decisão: se o app vai ter conteúdo com número variável em algum "
        "lugar (\"X itens no carrinho\", \"Y comentários\") ou preço/data formatados, "
        "isso sozinho já paga a lib. Se for só texto estático sem plural nem número, "
        "um dicionário simples aguenta por mais tempo — mas com 3 idiomas e produto "
        "crescendo, eu apostaria que o plural aparece rápido.")
    return ep


def lc_20(E):
    ep = E("LC", "lc-20-server-actions-vs-api-routes-en", lang="en")
    ep.user("for a new form submission feature, should we use a Server Action or just build an API route? genuinely not sure what the tradeoff is anymore")
    ep.final(
        "The honest tradeoff, since the marketing around Server Actions sometimes "
        "oversimplifies it: Server Actions are the better default for form-tied "
        "mutations SPECIFICALLY, and API routes remain the right choice the moment "
        "something outside a form needs to call the same logic.\n\n"
        "**Why Server Actions fit form submission well:** they're colocated with the "
        "form component (no separate route file to maintain), work with progressive "
        "enhancement (the form can submit even before JS hydrates, since it's backed "
        "by an actual HTML form action), and integrate with `useFormState`/"
        "`useFormStatus` for pending/error UI without you wiring up fetch + loading "
        "state by hand. For \"user submits a form, server does something, maybe "
        "redirects\" — that's the exact shape Server Actions were built for.\n\n"
        "**Where API routes are still the right call:** the moment the same logic "
        "needs to be called from somewhere that ISN'T a form in your app — a mobile "
        "client, a webhook from a third-party service, a public API consumed by "
        "someone else's code, or even just a `fetch` from client-side JS that isn't "
        "form-shaped. Server Actions are RPC-style functions callable from React "
        "components in your app; they're not meant to be a public HTTP contract "
        "documented and versioned for external consumers.\n\n"
        "**Practical rule I'd use:** if the mutation is triggered by a form submit "
        "inside this Next app and nothing outside the app needs to call it — Server "
        "Action, less ceremony, gets progressive enhancement for free. If literally "
        "anything else needs to hit that same logic (webhook, external client, public "
        "API) — API route, because that's the contract those callers expect. Worth "
        "noting you can also call the SAME underlying function from both a Server "
        "Action and an API route handler if you factor the actual logic out — the "
        "choice isn't \"duplicate the code,\" it's \"which entry point wraps the shared "
        "logic.\"")
    return ep


def lc_21(E):
    ep = E("LC", "lc-21-acessibilidade-desde-o-inicio")
    ep.user("Sinceramente acho que acessibilidade é coisa pra empresa grande se preocupar depois, a gente é 3 devs e precisa lançar rápido. Concorda?")
    ep.final(
        "Vou discordar, mas com um argumento de custo, não de princípio moral — porque "
        "\"depois\" e \"agora\" não custam o mesmo, e a diferença é maior do que parece "
        "com 3 devs.\n\n"
        "**Por que não é \"coisa pra empresa grande\":** a maior parte de acessibilidade "
        "básica (a que cobre 80% do valor) não é feature separada que você adiciona "
        "depois — é HÁBITO de como você escreve o componente na hora: usar `<button>` "
        "em vez de `<div onClick>`, dar `alt` em imagem, associar `<label>` a input, "
        "manter contraste de cor decente, não remover o focus ring sem substituir. "
        "Nenhum desses exige mais tempo de desenvolvimento que a alternativa ruim — é "
        "literalmente a mesma quantidade de código, só escrito do jeito certo desde o "
        "início.\n\n"
        "**Onde \"depois\" fica genuinamente caro:** o custo de retrofit não é linear "
        "com o tamanho do app, é pior — quando vocês tiverem 50 componentes escritos "
        "com `<div onClick>` em vez de `<button>`, corrigir depois significa auditar "
        "50 componentes, não escrever 50 direito da primeira vez. É a mesma lógica de "
        "dívida técnica: o juro composto de um hábito ruim replicado em cada "
        "componente novo.\n\n"
        "**Onde eu concordaria com você:** acessibilidade AVANÇADA (suporte completo a "
        "leitor de tela em interações complexas tipo drag-and-drop, testes "
        "automatizados de a11y no CI, auditoria com usuário real) — isso sim é "
        "razoável adiar pra quando o produto validar e crescer. Não é \"tudo ou nada\".\n\n"
        "Proposta prática pros 3 de vocês: adotem só os hábitos básicos (que não "
        "custam tempo extra) desde já, e adiem a parte avançada sem culpa. Vocês "
        "lançam no mesmo prazo, e não acumulam uma dívida que fica mais cara a cada "
        "componente que passa.")
    return ep


EPISODES = [
    l1_24, l1_25, l1_26,
    l2_22, l2_23, l2_24, l2_25,
    l3_19, l3_20,
    l4_19, l4_20, l4_21,
    l5_20, l5_21, l5_22,
    lc_19, lc_20, lc_21,
]
