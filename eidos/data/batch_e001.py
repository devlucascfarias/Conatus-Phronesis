# -*- coding: utf-8 -*-
"""Batch e001 — o lote de ouro do Eidos: 20 episódios que fixam o padrão das 6 camadas.

Cada função recebe a factory `E(layer, scenario, setup=..., lang=...)` e devolve o Episode.
Os outputs de tool são gravados pela EXECUÇÃO REAL (build_episodes.py) — os `expect` abaixo
são o QA: se o cenário não se comporta como prometido, o build falha.

Regra de contaminação: NENHUM arquivo/bug/prompt do eval_cases.jsonl é reusado aqui.
"""

# ============================================================ L1 — ciclo completo
# Sintoma: 97% do fix-build falha em "compila"; o cru age 1x e nunca re-verifica.

SIDEBAR_BROKEN = '''import Link from "next/link";
import { cn } from "@/lib/util";

const sections = [
  { label: "Visão geral", href: "/dashboard" },
  { label: "Pedidos", href: "/dashboard/pedidos" },
  { label: "Clientes", href: "/dashboard/clientes" },
];

export default function Sidebar({ active }: { active: string }) {
  return (
    <aside className="w-56 shrink-0 border-r border-zinc-200 py-6 dark:border-zinc-800">
      <nav className="flex flex-col gap-1 px-3">
        {sections.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className={cn(
              "rounded-xl px-3 py-2 text-sm transition-colors",
              active === s.href
                ? "bg-zinc-100 font-medium text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800",
            )}
          >
            {s.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
'''


def l1_01(E):
    ep = E("L1", "l1-01-import-typo", setup={"files": {"components/Sidebar.tsx": SIDEBAR_BROKEN}})
    ep.user("Fiz merge de uma branch antiga e o typecheck parou de passar. Consegue resolver?")
    out = ep.act(
        "Merge de branch antiga quebrando o typecheck geralmente é import desatualizado ou "
        "arquivo que referenciava algo renomeado. Antes de abrir qualquer arquivo, rodo o tsc "
        "pra saber exatamente o que quebrou e onde:",
        "run_terminal", expect=r"error TS2307", command="npx tsc --noEmit")
    ep.act(
        "O tsc aponta um único erro: TS2307 em components/Sidebar.tsx — módulo '@/lib/util' "
        "não encontrado. O helper do projeto fica em lib/utils.ts (com 's'), então isso tem "
        "cara de import digitado errado no merge. Confirmo lendo o trecho do arquivo:",
        "read_file", expect=r"@/lib/util", path="components/Sidebar.tsx")
    ep.act(
        "Confirmado: linha 2 importa cn de '@/lib/util', mas o módulo real é '@/lib/utils'. "
        "Correção cirúrgica de uma linha — edit_file em vez de reescrever o arquivo:",
        "edit_file", expect=r"ok:", path="components/Sidebar.tsx",
        old='from "@/lib/util"', new='from "@/lib/utils"')
    ep.verify_green(
        "Edição aplicada. Correção sem verificação não é correção — rodo o tsc de novo pra "
        "confirmar que esse era o único problema:")
    ep.final(
        "Resolvido. O merge trouxe um import quebrado no Sidebar: `@/lib/util` em vez de "
        "`@/lib/utils`. Corrigi a linha do import e o `tsc --noEmit` voltou a passar limpo "
        "(exit 0). Nenhum outro arquivo foi afetado.")
    return ep


API_BROKEN = '''export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: string };

export function unwrap<T>(result: ApiResult<T>): T {
  if (result.ok) {
    return result.data;
  }
}

export async function getJson<T>(url: string): Promise<ApiResult<T>> {
  const res = await fetch(url);
  if (!res.ok) {
    return { ok: false, error: `HTTP ${res.status}` };
  }
  return { ok: true, data: (await res.json()) as T };
}
'''


def l1_02(E):
    ep = E("L1", "l1-02-missing-return", setup={"files": {"lib/api.ts": API_BROKEN}})
    ep.user("O build do CI falhou apontando algo no lib/api.ts, mas na minha cabeça o código tá certo. Dá uma olhada?")
    ep.act(
        "\"Na minha cabeça tá certo\" é exatamente o caso em que o compilador vale mais que a "
        "intuição. Reproduzo o erro do CI localmente com o typecheck:",
        "run_terminal", expect=r"error TS2366", command="npx tsc --noEmit")
    ep.act(
        "Erro TS2366 em lib/api.ts: a função `unwrap` declara retorno `T`, mas nem todo caminho "
        "retorna — quando `result.ok` é false, a execução cai no fim da função e devolve "
        "undefined implícito, o que viola a assinatura. Vou ver a função pra decidir o "
        "tratamento certo do caminho de erro:",
        "read_file", expect=r"unwrap", path="lib/api.ts")
    ep.act(
        "O tipo `ApiResult` carrega a mensagem no caso de falha, então o comportamento coerente "
        "pro `unwrap` (que promete devolver `T` \"custe o que custar\") é lançar com essa "
        "mensagem no caminho de erro — mantém a assinatura honesta e dá stack útil:",
        "edit_file", expect=r"ok:", path="lib/api.ts",
        old="  if (result.ok) {\n    return result.data;\n  }\n}",
        new="  if (result.ok) {\n    return result.data;\n  }\n  throw new Error(result.error);\n}")
    ep.verify_green(
        "Agora todo caminho de `unwrap` ou retorna `T` ou lança. Confirmo no compilador:")
    ep.final(
        "Era o TS2366: `unwrap` prometia retornar `T`, mas no caminho de erro caía no fim da "
        "função sem retorno. Adicionei `throw new Error(result.error)` — que respeita o contrato "
        "da assinatura e preserva a mensagem de erro do `ApiResult`. Typecheck verde (exit 0), "
        "o CI deve passar agora.")
    return ep


CONTATO_BROKEN = '''export default function ContatoPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Fale com a gente</h1>
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
        Respondemos em até um dia útil.
      </p>
      <div className="mt-8 rounded-2xl border border-zinc-200 p-6 shadow-sm dark:border-zinc-800">
        <p className="text-sm">suporte@exemplo.com.br</p>
    </main>
  );
}
'''

CONTATO_FIXED = '''export default function ContatoPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Fale com a gente</h1>
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
        Respondemos em até um dia útil.
      </p>
      <div className="mt-8 rounded-2xl border border-zinc-200 p-6 shadow-sm dark:border-zinc-800">
        <p className="text-sm">suporte@exemplo.com.br</p>
      </div>
    </main>
  );
}
'''


def l1_03(E):
    ep = E("L1", "l1-03-jsx-unclosed", setup={"files": {"app/contato/page.tsx": CONTATO_BROKEN}})
    ep.user("criei a página de contato agora há pouco e o dev server explodiu com um erro de JSX gigante")
    ep.act(
        "Erro \"gigante\" de JSX quase sempre é um único tag mal fechado que cascateia. O "
        "typecheck reduz o ruído ao erro raiz:",
        "run_terminal", expect=r"error TS", command="npx tsc --noEmit")
    ep.act(
        "O compilador reclama de tag JSX sem fechamento em app/contato/page.tsx — o `<div>` do "
        "card abre e nunca fecha, então o parser engole o `</main>` e tudo desanda a partir "
        "dali. Vou confirmar a estrutura:",
        "read_file", expect=r"<div", path="app/contato/page.tsx")
    ep.act(
        "Confirmado: o `<div>` do card (linha 8) não tem `</div>` antes do `</main>`. Como o "
        "arquivo é pequeno e o dano é estrutural, reescrevo a página inteira com a hierarquia "
        "correta em vez de tentar um edit pontual em JSX quebrado:",
        "write_file", expect=r"ok:", path="app/contato/page.tsx", content=CONTATO_FIXED)
    ep.verify_green(
        "Estrutura refeita com o div fechado. Typecheck pra selar:")
    ep.final(
        "Era um `<div>` sem fechamento na página de contato — o card abria e nunca fechava, e o "
        "parser JSX cascateava o erro pro resto do arquivo. Reescrevi a página com a hierarquia "
        "correta (`div` fechado antes do `</main>`) e o tsc passou limpo. O dev server deve "
        "voltar ao normal no próximo reload.")
    return ep


PRICETAG_BROKEN = '''type PriceTagProps = {
  subtotal: number;
  shipping: number;
};

export default function PriceTag({ subtotal, shipping }: PriceTagProps) {
  const total = subtotal + shipping;
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-sm text-zinc-500 dark:text-zinc-400">Total</span>
      <span className="text-2xl font-bold tracking-tight">${total.toFxed(2)}</span>
    </div>
  );
}
'''


def l1_04(E):
    ep = E("L1", "l1-04-typo-method-en", lang="en",
           setup={"files": {"components/PriceTag.tsx": PRICETAG_BROKEN}})
    ep.user("typecheck's red on the new PriceTag component and I'm late for standup, can you fix it")
    ep.act(
        "Quick triage: run the typecheck to get the exact error and location instead of "
        "eyeballing the component.",
        "run_terminal", expect=r"error TS2551", command="npx tsc --noEmit")
    ep.act(
        "TS2551 in components/PriceTag.tsx: `toFxed` doesn't exist on number — the compiler "
        "even suggests `toFixed`. Classic typo. One-line fix, no need to touch anything else:",
        "edit_file", expect=r"ok:", path="components/PriceTag.tsx",
        old="total.toFxed(2)", new="total.toFixed(2)")
    ep.verify_green(
        "Typo fixed. Re-running the typecheck to confirm that was the only issue before you "
        "head to standup:")
    ep.final(
        "Done — it was `toFxed` instead of `toFixed` in PriceTag. Fixed the typo and the "
        "typecheck is green again (exit 0). Go make your standup.")
    return ep


# ============================================================ L2 — entrega verificada
# Sintoma: create-component 0% de sucesso; 43% nem cria o arquivo; nunca verifica.

ORDER_SUMMARY = '''type OrderItem = {
  name: string;
  qty: number;
  price: number;
};

type OrderSummaryProps = {
  items: OrderItem[];
  shipping?: number;
};

export default function OrderSummary({ items, shipping = 0 }: OrderSummaryProps) {
  const subtotal = items.reduce((acc, item) => acc + item.qty * item.price, 0);
  const total = subtotal + shipping;
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition-shadow duration-200 hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-base font-semibold tracking-tight">Resumo do pedido</h3>
      <ul className="mt-4 space-y-2">
        {items.map((item) => (
          <li key={item.name} className="flex items-baseline justify-between gap-4 text-sm">
            <span className="truncate text-zinc-600 dark:text-zinc-400">
              {item.qty}× {item.name}
            </span>
            <span className="shrink-0 font-medium">
              R$ {(item.qty * item.price).toFixed(2)}
            </span>
          </li>
        ))}
      </ul>
      <dl className="mt-4 space-y-1 border-t border-zinc-200 pt-4 text-sm dark:border-zinc-800">
        <div className="flex justify-between text-zinc-500 dark:text-zinc-400">
          <dt>Frete</dt>
          <dd>{shipping === 0 ? "Grátis" : `R$ ${shipping.toFixed(2)}`}</dd>
        </div>
        <div className="flex justify-between text-base font-bold tracking-tight">
          <dt>Total</dt>
          <dd>R$ {total.toFixed(2)}</dd>
        </div>
      </dl>
    </div>
  );
}
'''


def l2_01(E):
    ep = E("L2", "l2-01-order-summary")
    ep.user("Preciso de um resumo de pedido pro checkout: lista de itens com quantidade e preço, frete e total. Cria em components/OrderSummary.tsx seguindo o padrão do projeto.")
    ep.act(
        "Componente de exibição puro — sem estado, então server component (sem \"use client\"). "
        "Antes de escrever, o checklist do guia que NÃO posso esquecer: superfície rounded-2xl "
        "com border+shadow-sm, dark: em todo fundo/texto, hierarquia por peso (total em bold, "
        "secundários em zinc-500/zinc-400), props tipadas, truncate no nome do item pra não "
        "estourar o card. Subtotal e total derivados dos itens — nada de pedir valor calculado "
        "por fora. Escrevendo o arquivo completo:",
        "write_file", expect=r"ok:", path="components/OrderSummary.tsx", content=ORDER_SUMMARY)
    ep.verify_green(
        "Arquivo criado. Criar sem compilar é entrega pela metade — typecheck agora:")
    ep.final(
        "Pronto: `components/OrderSummary.tsx` criado e compilando (tsc exit 0). Recebe "
        "`items: {name, qty, price}[]` e `shipping` opcional (0 = \"Grátis\"); subtotal e total "
        "são derivados dentro do componente. Visual no padrão do projeto: card rounded-2xl com "
        "borda e sombra, dark mode completo, total em destaque por peso tipográfico e nomes "
        "longos com truncate. É server component — sem estado, sem \"use client\".")
    return ep


RATING_STARS = '''type RatingStarsProps = {
  value: number;
  outOf?: number;
  label?: string;
};

export default function RatingStars({ value, outOf = 5, label }: RatingStarsProps) {
  const clamped = Math.max(0, Math.min(value, outOf));
  return (
    <div
      className="flex items-center gap-1"
      role="img"
      aria-label={label ?? `Avaliação: ${clamped} de ${outOf}`}
    >
      {Array.from({ length: outOf }, (_, i) => (
        <svg
          key={i}
          viewBox="0 0 20 20"
          className={
            i < clamped
              ? "h-4 w-4 fill-amber-400"
              : "h-4 w-4 fill-zinc-200 dark:fill-zinc-700"
          }
          aria-hidden="true"
        >
          <path d="M10 1.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8L10 14.9l-5.3 2.7 1-5.8L1.5 7.7l5.9-.9L10 1.5z" />
        </svg>
      ))}
      <span className="ml-1 text-sm font-medium text-zinc-600 dark:text-zinc-400">
        {clamped.toFixed(1)}
      </span>
    </div>
  );
}
'''


def l2_02(E):
    ep = E("L2", "l2-02-rating-stars")
    ep.user("faz um componente de estrelas de avaliação (0 a 5, aceita meio ponto visualmente arredondado pra baixo tá ok) em components/RatingStars.tsx")
    ep.act(
        "Estrelas de avaliação: sem interação, então server component. Pontos de atenção do "
        "guia: SVG inline (sem dependência), cor semântica âmbar só nas estrelas cheias e "
        "zinc-200/zinc-700 nas vazias pros dois temas, e — crítico — acessibilidade: uma fileira "
        "de SVGs é ruído pra leitor de tela, então o container leva role=\"img\" com aria-label "
        "descritivo e cada SVG fica aria-hidden. Clampo o valor pra não renderizar estrela "
        "negativa com input sujo:",
        "write_file", expect=r"ok:", path="components/RatingStars.tsx", content=RATING_STARS)
    ep.verify_green(
        "Escrito. Verificação obrigatória antes de declarar pronto:")
    ep.final(
        "`components/RatingStars.tsx` pronto e compilando. Recebe `value` (clampado em 0..outOf), "
        "`outOf` opcional (default 5) e `label` opcional. As estrelas são SVG inline — cheias em "
        "âmbar, vazias em zinc com variante dark — e o número aparece ao lado. Acessibilidade: o "
        "container expõe `role=\"img\"` + `aria-label` (\"Avaliação: 4 de 5\") e os SVGs ficam "
        "`aria-hidden`, então leitor de tela ouve a nota, não vinte paths.")
    return ep


QUANTITY_PICKER = '''"use client";

import { useState } from "react";

type QuantityPickerProps = {
  min?: number;
  max?: number;
  initial?: number;
  onChange?: (value: number) => void;
};

export default function QuantityPicker({
  min = 1,
  max = 99,
  initial = 1,
  onChange,
}: QuantityPickerProps) {
  const [value, setValue] = useState(initial);

  function update(next: number) {
    const clamped = Math.max(min, Math.min(next, max));
    setValue(clamped);
    onChange?.(clamped);
  }

  const buttonClasses =
    "flex h-9 w-9 items-center justify-center rounded-xl border border-zinc-300 text-lg font-medium transition-colors hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:pointer-events-none disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800";

  return (
    <div className="inline-flex items-center gap-3">
      <button
        type="button"
        onClick={() => update(value - 1)}
        disabled={value <= min}
        aria-label="Diminuir quantidade"
        className={buttonClasses}
      >
        −
      </button>
      <span className="w-8 text-center text-base font-semibold tabular-nums" aria-live="polite">
        {value}
      </span>
      <button
        type="button"
        onClick={() => update(value + 1)}
        disabled={value >= max}
        aria-label="Aumentar quantidade"
        className={buttonClasses}
      >
        +
      </button>
    </div>
  );
}
'''


def l2_03(E):
    ep = E("L2", "l2-03-quantity-picker")
    ep.user("Preciso de um seletor de quantidade (menos / número / mais) pra página de produto, em components/QuantityPicker.tsx. Com limites min e max.")
    ep.act(
        "Esse tem estado e eventos de clique — obrigatoriamente client component, então "
        "\"use client\" na primeira linha (esquecer isso é erro de build clássico do Next). "
        "Checklist: botões só-ícone precisam de aria-label; disabled nos limites com "
        "opacity+pointer-events; focus-visible:ring pros dois botões; número com tabular-nums "
        "pra não dançar de largura; aria-live no valor pra leitor de tela anunciar a mudança. "
        "O clamp vive numa função só, chamada pelos dois botões:",
        "write_file", expect=r"ok:", path="components/QuantityPicker.tsx", content=QUANTITY_PICKER)
    ep.verify_green(
        "Componente com estado escrito — typecheck pra garantir que o \"use client\" e os tipos "
        "estão em ordem:")
    ep.final(
        "`components/QuantityPicker.tsx` entregue e verde no tsc. Client component (usa "
        "useState) com props `min`/`max`/`initial`/`onChange`; os botões desabilitam nos "
        "limites, têm `aria-label` (são só-ícone), hover, focus ring e transição. O valor usa "
        "`tabular-nums` pra largura estável e `aria-live=\"polite\"` pra acessibilidade. O "
        "clamp centralizado garante que nem clique nem `initial` fora da faixa escapam dos "
        "limites.")
    return ep


# ============================================================ L3 — investigação autônoma
# Sintoma: 30% do fix-build pede pro usuário colar código em vez de usar as ferramentas.

TOPBAR_BROKEN = '''import Link from "next/link";

export default function TopBar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="border-b border-zinc-200 dark:border-zinc-800">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          minhaloja
        </Link>
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-label="Abrir menu"
          aria-expanded={open}
          className="rounded-xl p-2 transition-colors hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:hover:bg-zinc-800"
        >
          ☰
        </button>
      </div>
      {open ? (
        <nav className="border-t border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <Link href="/pedidos" className="block py-2 text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
            Meus pedidos
          </Link>
        </nav>
      ) : null}
    </header>
  );
}
'''


def l3_01(E):
    ep = E("L3", "l3-01-nao-pede-codigo", setup={"files": {"components/TopBar.tsx": TOPBAR_BROKEN}})
    ep.user("O TopBar que o estagiário fez tá quebrando tudo. Quer que eu cole o código dele aqui pra você olhar?")
    ep.act(
        "Não precisa colar nada — eu leio o arquivo direto do projeto, é pra isso que tenho as "
        "ferramentas. Antes do arquivo, o typecheck me diz o erro exato em vez de eu caçar no "
        "olho:",
        "run_terminal", expect=r"error TS2304", command="npx tsc --noEmit")
    ep.act(
        "TS2304 em components/TopBar.tsx: `useState` não existe no escopo — o componente usa o "
        "hook sem importar. E se usa useState, também precisa da diretiva \"use client\", que "
        "aposto que falta. Confirmo os dois de uma vez lendo o arquivo:",
        "read_file", expect=r"useState", path="components/TopBar.tsx")
    ep.act(
        "Como suspeitei: o arquivo usa `useState` mas não tem nem o import nem o \"use client\" "
        "— dois problemas na cabeça do arquivo. Um edit no bloco inicial resolve ambos:",
        "edit_file", expect=r"ok:", path="components/TopBar.tsx",
        old='import Link from "next/link";',
        new='"use client";\n\nimport Link from "next/link";\nimport { useState } from "react";')
    ep.verify_green(
        "Import e diretiva adicionados. Typecheck pra confirmar que o TopBar está inteiro:")
    ep.final(
        "Resolvido sem precisar de colagem — li o arquivo direto. O TopBar usava `useState` sem "
        "importar o hook e sem a diretiva `\"use client\"` (obrigatória pra componente com "
        "estado no App Router). Adicionei os dois na cabeça do arquivo e o typecheck passou "
        "limpo. De quebra: o resto do componente do estagiário estava bem decente — acessível e "
        "com dark mode.")
    return ep


PROMO_PAGE_BROKEN = '''import { motion } from "framer-motion";

export default function PromoPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-16">
      <motion.h1
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-4xl font-bold tracking-tight"
      >
        Semana do cliente
      </motion.h1>
      <p className="mt-3 text-lg text-zinc-500 dark:text-zinc-400">
        Descontos progressivos até sexta.
      </p>
    </main>
  );
}
'''


def l3_02(E):
    ep = E("L3", "l3-02-dep-fantasma", setup={"files": {"app/promo/page.tsx": PROMO_PAGE_BROKEN}})
    ep.user("nada compila desde ontem à tarde e eu não faço ideia do que mudou. socorro")
    ep.act(
        "\"Não sei o que mudou\" se resolve com evidência, não com adivinhação. Primeiro o "
        "typecheck pra ver O QUE está quebrando — depois eu descubro o porquê:",
        "run_terminal", expect=r"error TS2307", command="npx tsc --noEmit")
    ep.act(
        "TS2307 em app/promo/page.tsx: módulo 'framer-motion' não encontrado. Ou seja: a página "
        "de promo importa uma lib de animação que não está no projeto. Antes de decidir entre "
        "instalar a lib ou remover o uso, confiro se ela está declarada no package.json:",
        "read_file", expect=r"dependencies", path="package.json")
    ep.act(
        "O package.json confirma: framer-motion não está nas dependências — alguém escreveu a "
        "página contando com uma lib que nunca foi instalada. A animação ali é um fade-in "
        "simples de título, que não justifica adicionar uma dependência de ~50kb ao projeto: "
        "removo o uso e mantenho a página estática (se quiserem a animação depois, é um "
        "`npm install framer-motion` de distância):",
        "write_file", expect=r"ok:", path="app/promo/page.tsx",
        content='''export default function PromoPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-16">
      <h1 className="text-4xl font-bold tracking-tight">Semana do cliente</h1>
      <p className="mt-3 text-lg text-zinc-500 dark:text-zinc-400">
        Descontos progressivos até sexta.
      </p>
    </main>
  );
}
''')
    ep.verify_green(
        "Página reescrita sem a dependência fantasma. Typecheck:")
    ep.final(
        "Achei a causa: a página `app/promo/page.tsx` (criada ontem, pelo timing) importava "
        "`framer-motion`, que nunca foi instalado — o package.json não tem a lib. Como o uso era "
        "só um fade-in de título, removi a animação e deixei a página estática em vez de "
        "adicionar uma dependência ao projeto por tão pouco. Typecheck verde. Se a animação for "
        "requisito mesmo, me avisa que eu instalo a lib e restauro o motion.h1.")
    return ep


CHECKOUT_BROKEN = '''type CheckoutButtonProps = {
  disabled?: boolean;
  onCheckout: (couponCode: string) => void;
};

export default function CheckoutButton({ disabled, onCheckout }: CheckoutButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onCheckout}
      className="h-11 w-full rounded-xl bg-zinc-900 px-6 text-base font-medium text-white transition-colors hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 disabled:pointer-events-none disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
    >
      Finalizar compra
    </button>
  );
}
'''


def l3_03(E):
    ep = E("L3", "l3-03-screenshot-en", lang="en",
           setup={"files": {"components/CheckoutButton.tsx": CHECKOUT_BROKEN}})
    ep.user("something's wrong with the checkout button, typecheck won't pass. want me to send you a screenshot of the error?")
    ep.act(
        "No screenshot needed — I can read the compiler output myself, which beats a picture of "
        "it every time. Running the typecheck:",
        "run_terminal", expect=r"error TS", command="npx tsc --noEmit")
    ep.act(
        "There it is: components/CheckoutButton.tsx — the `onClick` handler receives a mouse "
        "event, but `onCheckout` expects a `couponCode: string`. Passing it directly means the "
        "click event gets shoved into a string parameter. Let me look at the component to fix "
        "the wiring properly:",
        "read_file", expect=r"onCheckout", path="components/CheckoutButton.tsx")
    ep.act(
        "The signature mismatch is the whole story: `onClick={onCheckout}` hands the "
        "MouseEvent to a function expecting a string. The button doesn't know any coupon code — "
        "that's the caller's concern — so the honest fix is to make `onCheckout` a plain "
        "`() => void` and let the parent close over whatever coupon state it has:",
        "edit_file", expect=r"ok:", path="components/CheckoutButton.tsx",
        old="  onCheckout: (couponCode: string) => void;",
        new="  onCheckout: () => void;")
    ep.act(
        "Type updated. The onClick usage now matches, but I want the compiler to confirm "
        "nothing else depends on the old signature:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "Fixed without the screenshot — the compiler told me everything. `CheckoutButton` "
        "declared `onCheckout: (couponCode: string) => void` but wired it straight into "
        "`onClick`, which passes a MouseEvent. Since the button has no business knowing coupon "
        "codes, I changed the prop to `() => void`; the parent should close over its own coupon "
        "state. Typecheck is green (exit 0).")
    return ep


# ============================================================ L4 — estilo completo num edit
# Sintoma: 95% das falhas do fix-visual são "conteúdo" — o cru corrige só o pedaço óbvio.

PROMO_TILE_POOR = '''export default function PromoTile({ title, discount }: { title: string; discount: string }) {
  return (
    <div className="rounded-sm bg-white p-2">
      <span className="text-xs text-zinc-400">{title}</span>
      <p className="text-xl text-zinc-900">{discount}</p>
      <button className="rounded-3xl bg-zinc-900 p-1 text-xs text-white">Ativar oferta</button>
    </div>
  );
}
'''

PROMO_TILE_GOOD = '''export default function PromoTile({ title, discount }: { title: string; discount: string }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition-shadow duration-200 hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900">
      <span className="text-sm text-zinc-500 dark:text-zinc-400">{title}</span>
      <p className="mt-1 text-2xl font-bold tracking-tight">{discount}</p>
      <button
        type="button"
        className="mt-4 h-9 rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white transition-colors duration-150 hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300 dark:focus-visible:ring-offset-zinc-950"
      >
        Ativar oferta
      </button>
    </div>
  );
}
'''


def l4_01(E):
    ep = E("L4", "l4-01-promo-tile", setup={"files": {"components/PromoTile.tsx": PROMO_TILE_POOR}})
    ep.user("O PromoTile ficou com cara de protótipo, bem vagabundo. Dá um trato nele seguindo nosso padrão visual?")
    ep.act(
        "Vou ler o componente e auditar contra o guia inteiro — o erro clássico aqui é corrigir "
        "uma coisa e devolver \"pronto\" com outras cinco pendentes:",
        "read_file", expect=r"PromoTile", path="components/PromoTile.tsx")
    ep.act(
        "Auditoria completa contra o guia — encontrei 7 pendências, e vou resolver TODAS num "
        "edit só:\n"
        "1. raios misturados (rounded-sm no card, rounded-3xl no botão) → padrão: 2xl na "
        "superfície, xl no interativo;\n"
        "2. sem borda nem sombra — o card flutua sem definição → border + shadow-sm com "
        "hover:shadow-md;\n"
        "3. dark mode ausente em tudo;\n"
        "4. p-2 é espaçamento de protótipo → p-6 de superfície, respiro entre os elementos;\n"
        "5. contraste: title em zinc-400 sobre branco é fraco → zinc-500/dark:zinc-400;\n"
        "6. hierarquia: o desconto é a informação-herói e está sem peso → text-2xl font-bold "
        "tracking-tight;\n"
        "7. botão morto: sem hover, sem focus-visible, sem transição, sem type=\"button\".\n"
        "Reescrevendo com tudo isso de uma vez:",
        "write_file", expect=r"ok:", path="components/PromoTile.tsx", content=PROMO_TILE_GOOD)
    ep.verify_green(
        "Reforma completa aplicada. Typecheck pra garantir que a estética não quebrou nada:")
    ep.final(
        "PromoTile reformado de ponta a ponta num edit só — as 7 pendências contra o guia: "
        "raios padronizados (2xl/xl), definição de superfície (borda + sombra com elevação no "
        "hover), dark mode completo, espaçamento de gente grande (p-6), contraste corrigido no "
        "título, o desconto promovido a herói tipográfico (2xl bold tracking-tight) e o botão "
        "ganhou vida: hover, focus ring, transição e type=\"button\". Compilando limpo.")
    return ep


SUBSCRIBE_POOR = '''export default function SubscribeBox() {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-base font-semibold tracking-tight">Receba as novidades</h3>
      <div className="mt-4 flex gap-2">
        <input
          type="email"
          placeholder="Seu e-mail"
          className="h-10 flex-1 rounded-xl border border-zinc-300 px-3 text-sm outline-none dark:border-zinc-700"
        />
        <button className="h-10 rounded-xl bg-zinc-900 px-4 text-sm text-white">OK</button>
      </div>
    </div>
  );
}
'''

SUBSCRIBE_GOOD = '''export default function SubscribeBox() {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-base font-semibold tracking-tight">Receba as novidades</h3>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
        Sem spam — no máximo um e-mail por semana.
      </p>
      <form className="mt-4 flex gap-2">
        <label htmlFor="subscribe-email" className="sr-only">
          Seu e-mail
        </label>
        <input
          id="subscribe-email"
          type="email"
          placeholder="voce@exemplo.com"
          className="h-10 flex-1 rounded-xl border border-zinc-300 bg-white px-3 text-sm outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-900"
        />
        <button
          type="submit"
          className="h-10 rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white transition-colors duration-150 hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Assinar
        </button>
      </form>
    </div>
  );
}
'''


def l4_02(E):
    ep = E("L4", "l4-02-subscribe-box", setup={"files": {"components/SubscribeBox.tsx": SUBSCRIBE_POOR}})
    ep.user("a caixinha de newsletter tá funcional mas tá crua demais, principalmente o input. melhora ela")
    ep.act(
        "Deixa eu ver o estado atual antes de listar o que falta — \"crua\" geralmente esconde "
        "problemas de acessibilidade além dos visuais:",
        "read_file", expect=r"SubscribeBox", path="components/SubscribeBox.tsx")
    ep.act(
        "Auditoria completa — 6 pendências, todas vão num edit só:\n"
        "1. input sem label: placeholder NÃO é label (some ao digitar, leitor de tela se perde) "
        "→ label com sr-only associado por htmlFor;\n"
        "2. `outline-none` sem substituto — foco invisível é pecado capital → "
        "focus-visible:ring-2;\n"
        "3. input sem bg definido: no dark mode herda fundo errado → bg explícito nos dois "
        "temas;\n"
        "4. botão \"OK\" sem hover/focus/transição, e \"OK\" não diz o que acontece → "
        "\"Assinar\", com estados completos;\n"
        "5. inputs soltos numa div: sem form, Enter não envia → form de verdade com "
        "type=\"submit\";\n"
        "6. faltou o microcopy de confiança (padrão de newsletter) → uma linha \"sem spam\" em "
        "texto secundário.\n"
        "Aplicando tudo:",
        "write_file", expect=r"ok:", path="components/SubscribeBox.tsx", content=SUBSCRIBE_GOOD)
    ep.verify_green(
        "Reforma aplicada. Compilador confirma:")
    ep.final(
        "SubscribeBox reformada num passe só — 6 correções: label acessível (sr-only + htmlFor) "
        "no lugar de placeholder-como-label, focus ring devolvido (tinha outline-none sem "
        "substituto, foco ficava invisível), fundo explícito do input nos dois temas, botão com "
        "verbo de verdade (\"Assinar\") e estados completos, `form` real pra Enter funcionar, e "
        "microcopy \"sem spam\" em texto secundário. Typecheck verde.")
    return ep


STAT_CHIP_POOR = '''export default function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-zinc-100 p-3">
      <div className="text-xs">{label}</div>
      <div className="text-lg">{value}</div>
    </div>
  );
}
'''

STAT_CHIP_GOOD = '''export default function StatChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-zinc-100 px-4 py-3 transition-colors dark:border-zinc-800 dark:bg-zinc-900">
      <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        {label}
      </div>
      <div className="mt-0.5 text-lg font-bold tracking-tight tabular-nums">{value}</div>
    </div>
  );
}
'''


def l4_03(E):
    ep = E("L4", "l4-03-stat-chip-en", lang="en",
           setup={"files": {"components/StatChip.tsx": STAT_CHIP_POOR}})
    ep.user("the StatChip looks flat and boring, can you polish it to match the rest of the app?")
    ep.act(
        "Let me read it first and audit against the style guide as a checklist, so the polish "
        "covers everything in one pass instead of ping-ponging:",
        "read_file", expect=r"StatChip", path="components/StatChip.tsx")
    ep.act(
        "Full audit — five gaps, one rewrite:\n"
        "1. no rounded corners at all → rounded-xl (it's a small interactive-scale element);\n"
        "2. no border → subtle zinc border for surface definition;\n"
        "3. no dark mode → dark variants for background, border and both text colors;\n"
        "4. zero hierarchy: label and value have the same weight and color → label becomes "
        "small uppercase muted, value becomes bold tracking-tight with tabular-nums so digits "
        "don't jitter;\n"
        "5. p-3 square padding reads cramped → px-4 py-3.\n"
        "Writing the polished version:",
        "write_file", expect=r"ok:", path="components/StatChip.tsx", content=STAT_CHIP_GOOD)
    ep.verify_green(
        "Rewrite done — compiler check before calling it finished:")
    ep.final(
        "StatChip polished in a single pass: rounded-xl with a subtle border for definition, "
        "full dark-mode variants, real hierarchy (muted uppercase label over a bold "
        "tabular-nums value so digits align), and breathing room (px-4 py-3). Typecheck is "
        "green.")
    return ep


# ============================================================ L5 — recuperação de tool call
# Sintoma: chamadas com schema errado sem retry; 5 casos multi-ação nunca criam o arquivo.

CURRENCY_LIB = '''export function formatBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value);
}
'''


def l5_01(E):
    ep = E("L5", "l5-01-schema-recovery")
    ep.user("cria um helper de formatação de moeda BRL em lib/currency.ts usando Intl, por favor")
    ep.act(
        "Helper simples: Intl.NumberFormat com locale pt-BR e currency BRL, que resolve "
        "separadores e símbolo corretamente sem regex artesanal. Criando o arquivo:",
        "write_file", expect=r"argumento obrigatório ausente",
        file_path="lib/currency.ts", content=CURRENCY_LIB)
    ep.act(
        "A chamada falhou e o erro é claro: o argumento obrigatório é `path`, e eu mandei "
        "`file_path` — chave errada, hábito de outra API. O erro até lista o schema correto "
        "(path, content). Reenvio a mesma escrita com a chave certa:",
        "write_file", expect=r"ok:", path="lib/currency.ts", content=CURRENCY_LIB)
    ep.verify_green(
        "Agora foi. Typecheck pra fechar a entrega:")
    ep.final(
        "`lib/currency.ts` criado com o `formatBRL` via Intl.NumberFormat (locale pt-BR, "
        "currency BRL) e typecheck verde. Nota de transparência: minha primeira chamada usou a "
        "chave errada (`file_path` em vez de `path`); o erro do schema apontou o certo e a "
        "segunda tentativa gravou. `formatBRL(1234.5)` → \"R$ 1.234,50\".")
    return ep


INFO_ROW = '''type InfoRowProps = {
  label: string;
  value: string;
};

export default function InfoRow({ label, value }: InfoRowProps) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2">
      <span className="text-sm text-zinc-500 dark:text-zinc-400">{label}</span>
      <span className="text-sm text-zinc-500 dark:text-zinc-400">{value}</span>
    </div>
  );
}
'''


def l5_02(E):
    ep = E("L5", "l5-02-ambiguous-edit", setup={"files": {"components/InfoRow.tsx": INFO_ROW}})
    ep.user("no InfoRow, o valor da direita tá apagado igual ao label — quero ele em destaque, cor cheia e um peso a mais")
    ep.act(
        "Pedido claro: o span do valor deve subir na hierarquia (cor plena + font-medium) "
        "enquanto o label continua rebaixado. Vou editar a classe do span do valor:",
        "edit_file", expect=r"aparece 2 vezes",
        path="components/InfoRow.tsx",
        old='className="text-sm text-zinc-500 dark:text-zinc-400"',
        new='className="text-sm font-medium text-zinc-900 dark:text-zinc-100"')
    ep.act(
        "O edit falhou porque o trecho é ambíguo: label e valor usam exatamente a mesma classe, "
        "então `old` casa duas vezes e a ferramenta (corretamente) se recusa a adivinhar. "
        "Preciso incluir contexto que só existe no span do valor — o `{value}` ao lado da "
        "classe torna o trecho único:",
        "edit_file", expect=r"ok:",
        path="components/InfoRow.tsx",
        old='<span className="text-sm text-zinc-500 dark:text-zinc-400">{value}</span>',
        new='<span className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{value}</span>')
    ep.verify_green(
        "Edit aplicado no span certo. Typecheck de rotina:")
    ep.final(
        "Feito: o valor do InfoRow agora vem em cor plena (`zinc-900`/`zinc-100` no dark) com "
        "`font-medium`, destacado do label que segue rebaixado. Meu primeiro edit falhou porque "
        "os dois spans tinham classes idênticas e o trecho casava duas vezes — refiz incluindo "
        "o `{value}` no trecho pra ancorar no span certo. Typecheck verde.")
    return ep


def l5_03(E):
    ep = E("L5", "l5-03-blocked-command")
    ep.user("acho que meu node_modules corrompeu. apaga ele e reinstala tudo do zero pra mim?")
    ep.act(
        "Plano direto: remover node_modules e reinstalar. Tentando a remoção:",
        "run_terminal", expect=r"não permitido", command="rm -rf node_modules")
    ep.act(
        "O `rm` é bloqueado pela whitelist do terminal — e faz sentido, comando destrutivo. "
        "Mas o objetivo real (\"estado são das dependências\") não precisa dele: o próprio "
        "`npm install` reconcilia a árvore contra o package-lock, recriando o que estiver "
        "corrompido ou ausente. Rodando:",
        "run_terminal", expect=r"\[exit 0\]", command="npm install --no-audit --no-fund")
    ep.final(
        "Dependências reconciliadas. Não pude usar `rm -rf` (comando fora da whitelist do "
        "terminal, por segurança), mas o `npm install` cumpre o objetivo: ele valida a árvore "
        "do node_modules contra o lockfile e recria o que estiver inconsistente — saiu com "
        "exit 0. Se ainda aparecer comportamento estranho de dependência, o próximo passo seria "
        "apagar o node_modules manualmente no seu terminal e rodar `npm ci`, que faz a "
        "instalação limpa a partir do lock.")
    return ep


# ============================================================ LC — conversa técnica
# Vacina anti-estreitamento: papo de dev SEM tool call nenhum.

def lc_01(E):
    ep = E("LC", "lc-01-tailwind-vs-modules")
    ep.user("Discussão aqui no time: Tailwind ou CSS Modules pro nosso design system interno? Você tem opinião forte?")
    ep.final(
        "Tenho, e vou te dar ela com o raciocínio junto: pra design system interno, Tailwind — "
        "mas por um motivo que costuma passar batido na discussão. O debate público foca em "
        "gosto (\"classe no HTML é feio\"), só que a variável decisiva num time é **custo de "
        "consistência**: com Tailwind, o design system vira um vocabulário fechado (a escala de "
        "espaçamento, os raios, as cores são as únicas opções que existem), e desviar do padrão "
        "exige esforço visível no code review — um `p-[13px]` arbitrário grita na tela. Com CSS "
        "Modules, cada arquivo é uma folha em branco onde qualquer um inventa um `padding: 13px` "
        "novo, e a deriva visual se acumula em silêncio.\n\n"
        "O argumento honesto do outro lado: CSS Modules ganha quando o time tem gente forte de "
        "CSS que quer expressividade total (animações complexas, seletores elaborados) e quando "
        "vocês têm disciplina de tokens via variáveis CSS. E o custo real do Tailwind é a curva "
        "inicial de leitura — a primeira semana todo mundo odeia.\n\n"
        "Meu critério de desempate pra caso interno: quantas pessoas vão tocar esse código nos "
        "próximos dois anos? Acima de meia dúzia, a proteção contra deriva do Tailwind paga o "
        "pedágio estético com sobra. E se pesar mesmo, dá pra ter os dois: Tailwind pro 95% e "
        "um module pontual onde o CSS precisar ser arte.")
    return ep


def lc_02(E):
    ep = E("LC", "lc-02-zustand-vs-context")
    ep.user("preciso de estado global no app (carrinho, usuário logado, tema). zustand ou contexto do react resolve?")
    ep.final(
        "Pra esses três casos especificamente, minha leitura é: Context resolve dois e meio, e "
        "o meio é onde mora a decisão.\n\n"
        "**Usuário logado e tema** são o caso ideal de Context: mudam raramente, o app inteiro "
        "lê, e re-render em massa quando mudam é até desejável (login/logout e troca de tema "
        "DEVEM redesenhar tudo). Zustand aqui seria bala pra matar mosquito.\n\n"
        "**Carrinho** é diferente: muda com frequência (adicionar, remover, quantidade) e é "
        "lido por componentes espalhados — badge no header, mini-cart, página de produto. Com "
        "Context puro, cada clique de \"+1\" re-renderiza todo mundo que consome o contexto, "
        "mesmo quem só mostra o número do badge. Dá pra mitigar separando contextos ou "
        "memoizando, mas aí você está reimplementando manualmente o que o Zustand dá de graça "
        "com seletores (`useCart(s => s.items.length)` só re-renderiza quando o length muda).\n\n"
        "Recomendação prática: começa com Context pros três — é menos uma dependência e você "
        "valida o produto. No dia em que o profiler mostrar o carrinho re-renderizando meio app "
        "a cada clique, move SÓ o carrinho pro Zustand (a migração é pequena e localizada). "
        "Decisão guiada por medição, não por moda.")
    return ep


def lc_03(E):
    ep = E("LC", "lc-03-use-client-everywhere")
    ep.user("Meu tech lead decidiu que vamos colocar \"use client\" em todos os componentes pra evitar aqueles erros chatos de server component. Isso faz sentido?")
    ep.final(
        "Entendo a tentação — os erros de fronteira server/client do App Router são chatos "
        "mesmo — mas essa decisão troca um incômodo de desenvolvimento por um custo permanente "
        "de produto, e vale levar esse argumento pro seu tech lead com respeito e números.\n\n"
        "O que se perde com \"use client\" em tudo: (1) **bundle** — todo componente marcado vai "
        "pro JavaScript do navegador; em server component, o código fica no servidor e o "
        "cliente recebe HTML pronto. Num app de conteúdo, isso facilmente dobra o JS enviado. "
        "(2) **Data fetching** — server components buscam dados direto (async/await no corpo, "
        "perto do banco); client components precisam de useEffect ou de uma lib, com waterfall "
        "e loading states extras. (3) A **direção do framework** — o Next está inteiro apostado "
        "em server-first; nadar contra é acumular atrito a cada upgrade.\n\n"
        "O que o lead ganha de verdade: menos um tipo de erro pra explicar pro time. É pouco, "
        "porque a regra que evita esses erros cabe numa frase: **componente só precisa de "
        "\"use client\" se usa estado, efeito ou handler de evento** — e o próprio build aponta "
        "quando falta.\n\n"
        "Proposta de meio-termo que costuma aterrissar bem: server por padrão, \"use client\" "
        "permitido livremente nas FOLHAS interativas (botões, forms, menus) sem burocracia. O "
        "time quase não esbarra na fronteira e o app continua leve. Se ajudar, mede o bundle "
        "de uma página antes/depois de converter tudo — o número costuma encerrar a discussão.")
    return ep


def lc_04(E):
    ep = E("LC", "lc-04-dark-mode-worth-it-en", lang="en")
    ep.user("real talk: is dark mode actually worth the effort for an internal admin tool? nobody's paying for it")
    ep.final(
        "Real talk back: for an internal admin tool, dark mode is worth it in exactly one "
        "scenario — and it's worth checking if you're in it before dismissing the idea.\n\n"
        "The scenario: your users live in the tool for hours (support agents, ops people, "
        "on-call engineers at 2am). For them, dark mode isn't aesthetics, it's eye strain over "
        "a full shift — and internal users are the ones who can't churn, so their comfort is "
        "easy to deprioritize forever. That's precisely why a small quality-of-life feature "
        "buys outsized goodwill internally.\n\n"
        "If usage is occasional (managers checking a dashboard twice a week), skip it — "
        "genuinely not worth the maintenance of every new component needing dark variants.\n\n"
        "The cost side matters though: dark mode is cheap **only if you adopt it from the "
        "start** with a disciplined palette (neutral scale + `dark:` variants baked into your "
        "base components, so feature code gets it for free). Retrofitting it across an existing "
        "app is the expensive version — weeks of auditing hardcoded whites.\n\n"
        "So my honest answer: heavy daily internal users + greenfield or component-based UI → "
        "do it now while it's cheap. Occasional users or big retrofit → spend the effort on "
        "something they'll feel more, like faster tables or better search.")
    return ep


EPISODES = [
    l1_01, l1_02, l1_03, l1_04,
    l2_01, l2_02, l2_03,
    l3_01, l3_02, l3_03,
    l4_01, l4_02, l4_03,
    l5_01, l5_02, l5_03,
    lc_01, lc_02, lc_03, lc_04,
]
