# -*- coding: utf-8 -*-
"""Batch e002 — 20 episódios: padrões que faltaram no e001.

Novidades deste lote: erro em cascata com DUAS voltas de tsc (l1-06), o caso "use client"
que só o `next build` pega (l1-08), conserto criando o módulo ausente (l1-05), recuperação
de path errado (l5-04) e re-ancoragem de edit com releitura (l5-05).
"""

# ============================================================ L1 — ciclo completo

FILTERBAR_BROKEN = '''import { formatShortDate } from "@/lib/datetime";

type FilterBarProps = {
  from: Date;
  to: Date;
  onClear: () => void;
};

export default function FilterBar({ from, to, onClear }: FilterBarProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 px-4 py-2 text-sm dark:border-zinc-800">
      <span className="text-zinc-600 dark:text-zinc-400">
        {formatShortDate(from)} — {formatShortDate(to)}
      </span>
      <button
        type="button"
        onClick={onClear}
        className="rounded-lg px-2 py-1 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100"
      >
        Limpar
      </button>
    </div>
  );
}
'''

DATETIME_LIB = '''const shortDate = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
});

export function formatShortDate(date: Date): string {
  return shortDate.format(date);
}
'''


def l1_05(E):
    ep = E("L1", "l1-05-modulo-ausente", setup={"files": {"components/FilterBar.tsx": FILTERBAR_BROKEN}})
    ep.user("Subi o FilterBar da feature de relatórios e o typecheck começou a reclamar. Pode resolver?")
    ep.act(
        "Typecheck reclamando logo depois de um componente novo: ou o componente tem erro "
        "interno, ou referencia algo que ainda não existe. O tsc me diz qual dos dois:",
        "run_terminal", expect=r"error TS2307", command="npx tsc --noEmit")
    ep.act(
        "TS2307: o FilterBar importa `formatShortDate` de '@/lib/datetime', e esse módulo não "
        "existe no projeto. Dois caminhos: remover o uso ou criar o helper. Vou ver como o "
        "componente usa a função pra decidir:",
        "read_file", expect=r"formatShortDate", path="components/FilterBar.tsx")
    ep.act(
        "O componente formata um intervalo de datas pro usuário — o helper é legítimo e vai "
        "servir pra outros lugares (relatórios têm data em tudo). Então o conserto certo é "
        "criar o módulo, não amputar o componente. Intl.DateTimeFormat com locale pt-BR, "
        "instanciado UMA vez fora da função (criar formatter a cada render é desperdício):",
        "write_file", expect=r"ok:", path="lib/datetime.ts", content=DATETIME_LIB)
    ep.verify_green(
        "Módulo criado. Typecheck pra confirmar que o import resolve e as assinaturas batem:")
    ep.final(
        "Resolvido criando o que faltava: o FilterBar importava `formatShortDate` de "
        "`@/lib/datetime`, que ainda não existia. Criei o módulo com Intl.DateTimeFormat "
        "(pt-BR, dia + mês abreviado), com o formatter instanciado uma única vez no módulo — "
        "não a cada chamada. Typecheck verde; o helper fica disponível pro resto da feature de "
        "relatórios.")
    return ep


COUPON_BROKEN = '''import { cn } from "@/lib/utils";

type CouponBannerProps = {
  code: string;
  active: boolean;
};

export default function CouponBanner({ code, active }: CouponBannerProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-xl border px-4 py-3 text-sm",
        active
          ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
          : "border-zinc-200 bg-zinc-50 text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400",
      )}
    >
      <span className="font-mono font-semibold tracking-wide">{code.toUpperCase(3)}</span>
      <button type="button" onClick={dismiss} aria-label="Dispensar cupom">
        ×
      </button>
    </div>
  );
}
'''


def l1_06(E):
    ep = E("L1", "l1-06-cascata-dois-erros", setup={"files": {"components/CouponBanner.tsx": COUPON_BROKEN}})
    ep.user("o CouponBanner tá com erro de compilação, arruma pra mim?")
    out = ep.act(
        "Direto ao compilador — ele lista tudo de uma vez e me poupa de caçar erro no olho:",
        "run_terminal", expect=r"error TS2554.*\n.*error TS2304|error TS2304.*\n.*error TS2554|error TS",
        command="npx tsc --noEmit")
    ep.act(
        "Dois erros distintos no mesmo arquivo:\n"
        "1. TS2554: `code.toUpperCase(3)` — toUpperCase não aceita argumento; o 3 ali não faz "
        "sentido nenhum.\n"
        "2. TS2304: `dismiss` não existe — o botão de fechar referencia um handler que ninguém "
        "definiu.\n"
        "Vou resolver em ordem, um de cada vez, verificando entre eles. Primeiro o mais "
        "simples, a arity do toUpperCase:",
        "edit_file", expect=r"ok:", path="components/CouponBanner.tsx",
        old="code.toUpperCase(3)", new="code.toUpperCase()")
    ep.act(
        "Primeiro erro eliminado. Reconfirmo no tsc — importa ver que sobrou EXATAMENTE o "
        "segundo erro, e não algo novo:",
        "run_terminal", expect=r"error TS2304", command="npx tsc --noEmit")
    ep.act(
        "Como esperado, restou só o TS2304 do `dismiss`. Decisão de projeto: um handler de "
        "dispensar exigiria estado e \"use client\" — mas nada no banner pede interatividade "
        "além disso. Mais barato e mais correto manter o componente server e tirar o botão "
        "órfão; quem usar o banner controla a exibição por fora:",
        "edit_file", expect=r"ok:", path="components/CouponBanner.tsx",
        old='      <button type="button" onClick={dismiss} aria-label="Dispensar cupom">\n        ×\n      </button>\n',
        new="")
    ep.verify_green(
        "Segundo erro resolvido. Verificação final do ciclo:")
    ep.final(
        "Eram DOIS erros no CouponBanner, resolvidos um por vez com verificação entre eles: "
        "(1) `toUpperCase(3)` — o método não aceita argumento, virou `toUpperCase()`; "
        "(2) o botão de dispensar chamava um handler `dismiss` que não existia — removi o "
        "botão em vez de inventar estado, mantendo o componente server (quem renderiza o "
        "banner decide quando escondê-lo). Typecheck verde no fechamento.")
    return ep


VALIDATORS_BROKEN = '''export function isEmail(value: string): boolean {
  return EMAIL_RE.test(value.trim().toLowerCase());
}

export function isCep(value: string): boolean {
  return /^\\d{5}-?\\d{3}$/.test(value.trim());
}
'''


def l1_07(E):
    ep = E("L1", "l1-07-const-ausente", setup={"files": {"lib/validators.ts": VALIDATORS_BROKEN}})
    ep.user("extraí uns validadores pra lib/validators.ts e esqueci alguma coisa no meio do caminho, o tsc tá bravo")
    ep.act(
        "Extração de código é o habitat natural do \"esqueci de levar junto\". Vamos ver o que "
        "ficou pra trás:",
        "run_terminal", expect=r"error TS2304", command="npx tsc --noEmit")
    ep.act(
        "TS2304 em lib/validators.ts: `EMAIL_RE` não existe — na extração, a função `isEmail` "
        "veio mas a regex que ela usa ficou no arquivo de origem. O `isCep` logo abaixo usa "
        "regex inline, então o padrão do arquivo comporta os dois estilos; vou declarar a "
        "constante no topo, que documenta melhor uma regex não-trivial:",
        "edit_file", expect=r"ok:", path="lib/validators.ts",
        old="export function isEmail",
        new='const EMAIL_RE = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;\n\nexport function isEmail')
    ep.verify_green(
        "Constante restaurada. Typecheck:")
    ep.final(
        "Era isso: na extração pro `lib/validators.ts`, a função `isEmail` veio sem a regex "
        "`EMAIL_RE` que ela usa. Declarei a constante no topo do arquivo (validação pragmática "
        "de e-mail: algo@algo.algo, sem espaços) e o typecheck passou. Vale conferir depois se "
        "a `EMAIL_RE` original ficou órfã no arquivo de onde você extraiu.")
    return ep


LIKE_BUTTON_BROKEN = '''import { useState } from "react";

export default function LikeButton() {
  const [liked, setLiked] = useState(false);
  return (
    <button
      type="button"
      onClick={() => setLiked(!liked)}
      aria-pressed={liked}
      aria-label={liked ? "Descurtir" : "Curtir"}
      className={
        liked
          ? "rounded-xl bg-rose-100 px-3 py-1.5 text-sm font-medium text-rose-700 transition-colors dark:bg-rose-950 dark:text-rose-300"
          : "rounded-xl bg-zinc-100 px-3 py-1.5 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700"
      }
    >
      {liked ? "♥ Curtido" : "♡ Curtir"}
    </button>
  );
}
'''


PRODUTO_PAGE_USES_LIKE = '''import LikeButton from "@/components/LikeButton";

export default function ProdutoPage() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-16">
      <h1 className="text-3xl font-bold tracking-tight">Produto</h1>
      <div className="mt-6">
        <LikeButton />
      </div>
    </main>
  );
}
'''


def l1_08(E):
    ep = E("L1", "l1-08-use-client-build", setup={"files": {
        "components/LikeButton.tsx": LIKE_BUTTON_BROKEN,
        "app/produto/page.tsx": PRODUTO_PAGE_USES_LIKE,
    }})
    ep.user("Situação estranha: o tsc passa limpo, mas o next build falha no LikeButton. Como pode?")
    ep.act(
        "Pode, e é um caso clássico do App Router: a fronteira server/client NÃO é checada pelo "
        "tsc — tipos estão certos, mas o Next se recusa a compilar hook de estado em server "
        "component. Rodo o build pra ver o erro exato:",
        "run_terminal", expect=r"use client", command="npm run build")
    ep.act(
        "Confirmado: \"You're importing a component that needs useState... only works in a "
        "Client Component\". O LikeButton usa useState e onClick — interativo por natureza — "
        "mas não declara `\"use client\"`, então o Next o trata como server component e "
        "recusa o hook. A diretiva na primeira linha resolve:",
        "edit_file", expect=r"ok:", path="components/LikeButton.tsx",
        old='import { useState } from "react";',
        new='"use client";\n\nimport { useState } from "react";')
    ep.act(
        "Diretiva adicionada. A prova real desse caso é o build (o tsc nunca viu problema "
        "algum) — rodando de novo:",
        "run_terminal", expect=r"\[exit 0\]", command="npm run build")
    ep.final(
        "Mistério resolvido: a fronteira server/client do App Router é regra do Next, não do "
        "TypeScript — por isso o tsc passava e o build não. O LikeButton usa `useState` e "
        "`onClick` mas não declarava `\"use client\"`; adicionei a diretiva na primeira linha "
        "e o `next build` compilou até o fim (exit 0). Regra de bolso pra guardar: estado, "
        "efeito ou handler de evento ⇒ \"use client\" no topo.")
    return ep


# ============================================================ L2 — entrega verificada

INVOICE_LIST = '''type InvoiceStatus = "paga" | "pendente" | "vencida";

type Invoice = {
  id: string;
  cliente: string;
  valor: number;
  status: InvoiceStatus;
};

const statusStyles: Record<InvoiceStatus, string> = {
  paga: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  pendente: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  vencida: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300",
};

export default function InvoiceList({ invoices }: { invoices: Invoice[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-zinc-200 shadow-sm dark:border-zinc-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 text-left dark:border-zinc-800 dark:bg-zinc-900">
            <th className="px-4 py-3 font-medium text-zinc-500 dark:text-zinc-400">Fatura</th>
            <th className="px-4 py-3 font-medium text-zinc-500 dark:text-zinc-400">Cliente</th>
            <th className="px-4 py-3 text-right font-medium text-zinc-500 dark:text-zinc-400">Valor</th>
            <th className="px-4 py-3 font-medium text-zinc-500 dark:text-zinc-400">Status</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <tr
              key={inv.id}
              className="border-b border-zinc-100 transition-colors last:border-0 hover:bg-zinc-50 dark:border-zinc-800/60 dark:hover:bg-zinc-900"
            >
              <td className="px-4 py-3 font-mono text-xs text-zinc-500 dark:text-zinc-400">{inv.id}</td>
              <td className="px-4 py-3">{inv.cliente}</td>
              <td className="px-4 py-3 text-right font-medium tabular-nums">
                R$ {inv.valor.toFixed(2)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyles[inv.status]}`}
                >
                  {inv.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
'''


def l2_04(E):
    ep = E("L2", "l2-04-invoice-list")
    ep.user("Cria em components/InvoiceList.tsx uma listagem de faturas: id, cliente, valor e status (paga/pendente/vencida), com o status colorido por significado.")
    ep.act(
        "Listagem tabular sem interação de estado — server component. Decisões de projeto "
        "antes de escrever: status é união literal (\"paga\" | \"pendente\" | \"vencida\") com "
        "um Record de estilos — assim adicionar um status novo sem estilo vira erro de "
        "compilação, não bug silencioso. Cores semânticas nos dois temas (verde/âmbar/rosa), "
        "valores à direita com tabular-nums, hover na linha, e overflow-x-auto no wrapper pra "
        "tabela nunca estourar o layout no mobile:",
        "write_file", expect=r"ok:", path="components/InvoiceList.tsx", content=INVOICE_LIST)
    ep.verify_green(
        "Escrito — inclusive o Record tipado que quero que o compilador valide. Typecheck:")
    ep.final(
        "`components/InvoiceList.tsx` entregue e compilando. O status é união literal tipada "
        "com `Record<InvoiceStatus, string>` de estilos — se alguém criar um status novo sem "
        "cor, o tsc acusa na hora. Semântica de cor: paga=verde, pendente=âmbar, vencida=rosa, "
        "nos dois temas. Valores alinhados à direita com tabular-nums, hover sutil por linha, "
        "cabeçalho rebaixado e `overflow-x-auto` pro mobile. Server component puro.")
    return ep


COPY_FIELD = '''"use client";

import { useState } from "react";

type CopyFieldProps = {
  value: string;
  label: string;
};

export default function CopyField({ value, label }: CopyFieldProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      <div className="flex gap-2">
        <input
          readOnly
          value={value}
          aria-label={label}
          className="h-10 flex-1 rounded-xl border border-zinc-300 bg-zinc-50 px-3 font-mono text-sm text-zinc-600 outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400"
        />
        <button
          type="button"
          onClick={copy}
          className="h-10 w-24 rounded-xl border border-zinc-300 text-sm font-medium transition-colors hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          {copied ? "Copiado!" : "Copiar"}
        </button>
      </div>
    </div>
  );
}
'''


def l2_05(E):
    ep = E("L2", "l2-05-copy-field")
    ep.user("preciso de um campo de copiar (tipo aqueles de API key): input readonly + botão que copia e confirma. components/CopyField.tsx")
    ep.act(
        "Clipboard e feedback \"Copiado!\" exigem estado — client component com \"use client\". "
        "Detalhes que separam o bom do meia-boca aqui: o botão tem largura FIXA (w-24) pra não "
        "pular de tamanho quando o texto troca de \"Copiar\" pra \"Copiado!\"; o input é "
        "readOnly com fonte mono (valor técnico) e fundo rebaixado sinalizando não-editável; o "
        "feedback reverte sozinho após 2s. navigator.clipboard é async — o handler acompanha:",
        "write_file", expect=r"ok:", path="components/CopyField.tsx", content=COPY_FIELD)
    ep.verify_green(
        "Componente escrito. Typecheck antes de entregar:")
    ep.final(
        "`components/CopyField.tsx` pronto e verde no tsc. Client component: input readOnly em "
        "fonte mono com fundo rebaixado, botão de copiar com largura fixa (não dança quando "
        "vira \"Copiado!\"), feedback que se desfaz em 2s, focus ring nos dois elementos e "
        "clipboard via `navigator.clipboard.writeText` async. Props: `value` e `label` (o "
        "label também vira `aria-label` do input).")
    return ep


STATUS_PAGE = '''import type { Metadata } from "next";
import Card from "@/components/Card";
import Button from "@/components/Button";

export const metadata: Metadata = {
  title: "Status — Eidos",
  description: "Estado dos serviços da plataforma",
};

const services = [
  { name: "API", status: "Operacional", ok: true },
  { name: "Painel", status: "Operacional", ok: true },
  { name: "Webhooks", status: "Degradado", ok: false },
];

export default function StatusPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Status dos serviços</h1>
      <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
        Atualizado a cada 60 segundos.
      </p>
      <div className="mt-8 space-y-4">
        {services.map((svc) => (
          <Card key={svc.name} title={svc.name} description={svc.status}>
            <span
              className={
                svc.ok
                  ? "inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"
                  : "inline-flex h-2.5 w-2.5 rounded-full bg-amber-500"
              }
              aria-hidden="true"
            />
          </Card>
        ))}
      </div>
      <div className="mt-8">
        <Button variant="secondary">Assinar notificações</Button>
      </div>
    </main>
  );
}
'''


def l2_06(E):
    ep = E("L2", "l2-06-status-page")
    ep.user("Monta uma página de status dos serviços em app/status/page.tsx — pode usar os componentes que o projeto já tem.")
    ep.act(
        "Página nova no App Router: server component com `metadata` exportado (título e "
        "descrição próprios — página sem metadata é página invisível pra SEO e pra aba do "
        "navegador). \"Usar o que o projeto já tem\" é instrução que levo a sério: o Card e o "
        "Button do template resolvem a superfície e o CTA — reinventar componente existente é "
        "deriva visual. Indicador de status por cor semântica (verde/âmbar) com aria-hidden, "
        "já que o texto ao lado carrega a informação:",
        "write_file", expect=r"ok:", path="app/status/page.tsx", content=STATUS_PAGE)
    ep.verify_green(
        "Página composta com os componentes do projeto. Typecheck valida os imports e o tipo "
        "do metadata:")
    ep.final(
        "`app/status/page.tsx` criada e compilando. Server component com `Metadata` tipado "
        "(título \"Status — Eidos\"), lista de serviços renderizada com o `Card` do projeto e "
        "CTA com o `Button` variant secondary — zero componente novo inventado. O ponto de "
        "status usa cor semântica (verde operacional, âmbar degradado) com `aria-hidden`, "
        "porque a informação já está no texto do card.")
    return ep


KBD_HINT = '''type KbdHintProps = {
  keys: string[];
  action: string;
};

export default function KbdHint({ keys, action }: KbdHintProps) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
      <span className="inline-flex items-center gap-1">
        {keys.map((key, i) => (
          <kbd
            key={key}
            className="rounded-md border border-zinc-300 bg-zinc-50 px-1.5 py-0.5 font-mono text-xs font-medium text-zinc-700 shadow-[0_1px_0_1px_rgba(0,0,0,0.04)] dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
          >
            {key}
          </kbd>
        ))}
      </span>
      {action}
    </span>
  );
}
'''


def l2_07(E):
    ep = E("L2", "l2-07-kbd-hint-en", lang="en")
    ep.user("small one: a keyboard shortcut hint component (like \"Ctrl K to search\") for components/KbdHint.tsx")
    ep.act(
        "Small but with real semantics available: HTML has the `<kbd>` element for exactly "
        "this — using a styled span would throw away meaning for free. Design notes: keycaps "
        "get a mono font, subtle border and a hairline bottom shadow for that physical-key "
        "look, muted in both themes since hints are secondary UI. Props: `keys` as an array "
        "(so \"Ctrl\"+\"K\" renders as two caps) plus the `action` description:",
        "write_file", expect=r"ok:", path="components/KbdHint.tsx", content=KBD_HINT)
    ep.verify_green(
        "Written. Typecheck to close it out:")
    ep.final(
        "`components/KbdHint.tsx` done and compiling. Uses the semantic `<kbd>` element per "
        "keycap — mono font, subtle border, hairline shadow for a physical-key feel, muted "
        "colors in both themes. Takes `keys: string[]` (each renders as its own cap) and "
        "`action: string`, so `<KbdHint keys={[\"Ctrl\", \"K\"]} action=\"to search\" />` reads "
        "exactly like your example.")
    return ep


# ============================================================ L3 — investigação autônoma

def l3_04(E):
    ep = E("L3", "l3-04-roda-e-reporta")
    ep.user("acabei de clonar o projeto. roda aí e me diz se tá tudo ok antes de eu começar a mexer")
    ep.act(
        "Servidor de dev interativo não dá pra deixar rodando por aqui, mas consigo te dar um "
        "veredito honesto do estado do projeto com o typecheck — que pega o grosso do que "
        "estaria quebrado num clone:",
        "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")
    ep.final(
        "Pode mexer tranquilo: o typecheck passou limpo (exit 0) — nenhum erro de tipo, import "
        "quebrado ou JSX malformado no projeto inteiro. Transparência sobre o que isso cobre e "
        "o que não: o tsc valida o código, mas não executei o `next build` completo (mais "
        "lento; pega ainda fronteiras server/client e erros de configuração) nem o dev server. "
        "Se quiser a verificação completa antes de começar, rodo o build também — é um "
        "comando.")
    return ep


LOGIN_PANEL_BROKEN = '''export default function LoginPanel() {
  return (
    <div className="mx-auto max-w-sm rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-bold tracking-tight text-zinc-900">Entrar</h2>
      <form className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <label htmlFor="login-email" className="text-sm font-medium text-zinc-900">
            E-mail
          </label>
          <input
            id="login-email"
            type="email"
            className="h-10 w-full rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-900 outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="login-senha" className="text-sm font-medium text-zinc-900">
            Senha
          </label>
          <input
            id="login-senha"
            type="password"
            className="h-10 w-full rounded-xl border border-zinc-300 bg-white px-3 text-sm text-zinc-900 outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
          />
        </div>
        <button
          type="submit"
          className="h-10 w-full rounded-xl bg-zinc-900 text-sm font-medium text-white transition-colors hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
        >
          Entrar
        </button>
      </form>
    </div>
  );
}
'''

LOGIN_PANEL_FIXED = '''export default function LoginPanel() {
  return (
    <div className="mx-auto max-w-sm rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="text-xl font-bold tracking-tight">Entrar</h2>
      <form className="mt-6 space-y-4">
        <div className="space-y-1.5">
          <label htmlFor="login-email" className="text-sm font-medium">
            E-mail
          </label>
          <input
            id="login-email"
            type="email"
            className="h-10 w-full rounded-xl border border-zinc-300 bg-white px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="login-senha" className="text-sm font-medium">
            Senha
          </label>
          <input
            id="login-senha"
            type="password"
            className="h-10 w-full rounded-xl border border-zinc-300 bg-white px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-950"
          />
        </div>
        <button
          type="submit"
          className="h-10 w-full rounded-xl bg-zinc-900 text-sm font-medium text-white transition-colors hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Entrar
        </button>
      </form>
    </div>
  );
}
'''


def l3_05(E):
    ep = E("L3", "l3-05-some-no-dark", setup={"files": {"components/LoginPanel.tsx": LOGIN_PANEL_BROKEN}})
    ep.user("o formulário de login fica ilegível no tema escuro, tudo branco. não lembro nem em que arquivo ele tá")
    ep.act(
        "Não precisa lembrar — eu acho. \"Formulário de login\" no padrão de nomes deste "
        "projeto deve ser LoginForm ou LoginPanel em components/. Tento o primeiro:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/LoginForm.tsx")
    ep.act(
        "LoginForm não existe — tento a segunda hipótese de nome:",
        "read_file", expect=r"LoginPanel", path="components/LoginPanel.tsx")
    ep.act(
        "Achei, e o diagnóstico bate com o sintoma: o componente inteiro está hardcoded pro "
        "tema claro — `bg-white`, `text-zinc-900`, borda clara — sem UMA variante `dark:`. No "
        "tema escuro isso vira um bloco branco com texto escuro ilegível contra o fundo. A "
        "correção é sistemática (todo fundo, borda e texto precisa do par dark), então "
        "reescrevo o componente; aproveito e removo os `text-zinc-900` redundantes onde a cor "
        "já herda do body:",
        "write_file", expect=r"ok:", path="components/LoginPanel.tsx", content=LOGIN_PANEL_FIXED)
    ep.verify_green(
        "Dark mode aplicado em card, inputs e botão. Typecheck de praxe:")
    ep.final(
        "Encontrei sozinho: era `components/LoginPanel.tsx` (tentei LoginForm primeiro, não "
        "existia). O componente estava 100% hardcoded pro tema claro — nenhuma variante "
        "`dark:` em card, inputs ou botão. Reescrevi com os pares completos: card "
        "`dark:bg-zinc-900` com borda escura, inputs `dark:bg-zinc-950`, botão invertido "
        "(claro sobre escuro) no dark, e removi cores redundantes que já herdam do body. "
        "Typecheck verde — o login agora existe nos dois temas.")
    return ep


SHARE_MENU_BROKEN = '''type ShareMenuProps = {
  url: string;
  compact?: boolean;
};

const networks = [
  { name: "X", href: (u: string) => `https://x.com/intent/post?url=${u}` },
  { name: "LinkedIn", href: (u: string) => `https://www.linkedin.com/sharing/share-offsite/?url=${u}` },
];

export default function ShareMenu({ url, compact }: ShareMenuProps) {
  const encoded = encodeURIComponent(url);
  return (
    <nav aria-label="Compartilhar" className="flex items-center gap-2">
      {networks.map((n) => (
        <a
          key={n.name}
          href={n.href(encoded)}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "rounded-xl border border-zinc-300 text-sm font-medium transition-colors hover:bg-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 dark:border-zinc-700 dark:hover:bg-zinc-800",
            compact ? "px-2 py-1" : "px-3 py-1.5",
          )}
        >
          {n.name}
        </a>
      ))}
    </nav>
  );
}
'''


def l3_06(E):
    ep = E("L3", "l3-06-ci-repro-en", lang="en",
           setup={"files": {"components/ShareMenu.tsx": SHARE_MENU_BROKEN}})
    ep.user("CI is red on the frontend job. I could forward you the pipeline logs... actually can you just reproduce it locally? faster")
    ep.act(
        "Agreed — a local repro beats reading CI logs secondhand, and I have the tools for it. "
        "The frontend job's first gate is the typecheck, so that's where I start:",
        "run_terminal", expect=r"error TS2304", command="npx tsc --noEmit")
    ep.act(
        "Reproduced: TS2304 in components/ShareMenu.tsx — `cn` is used for the conditional "
        "classes but never imported. Whoever wrote it used the project's helper by muscle "
        "memory and forgot the import line. Confirming it's the only gap:",
        "read_file", expect=r"cn\(", path="components/ShareMenu.tsx")
    ep.act(
        "Yes — the component is otherwise sound (proper rel on external links, aria-label on "
        "the nav). Adding the missing import:",
        "edit_file", expect=r"ok:", path="components/ShareMenu.tsx",
        old="type ShareMenuProps = {",
        new='import { cn } from "@/lib/utils";\n\ntype ShareMenuProps = {')
    ep.verify_green(
        "Import added. Re-running the same check CI runs:")
    ep.final(
        "Reproduced and fixed locally: `ShareMenu.tsx` used the `cn()` helper without "
        "importing it — TS2304, which is exactly what was killing the CI job's typecheck "
        "step. Added the `@/lib/utils` import and tsc is green (exit 0). Push it and the "
        "pipeline should go back to green; no need to dig through the CI logs.")
    return ep


# ============================================================ L4 — estilo completo num edit

DELIVERY_POOR = '''type Step = { label: string; done: boolean };

export default function DeliverySteps({ steps }: { steps: Step[] }) {
  return (
    <ul>
      {steps.map((s) => (
        <li key={s.label} className="text-sm">
          <span>{s.done ? "ok" : "-"}</span> {s.label}
        </li>
      ))}
    </ul>
  );
}
'''

DELIVERY_GOOD = '''type Step = { label: string; done: boolean };

export default function DeliverySteps({ steps }: { steps: Step[] }) {
  return (
    <ul className="space-y-3">
      {steps.map((s) => (
        <li key={s.label} className="flex items-center gap-3 text-sm">
          <span
            aria-hidden="true"
            className={
              s.done
                ? "flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white"
                : "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-zinc-300 dark:border-zinc-700"
            }
          >
            {s.done ? "✓" : ""}
          </span>
          <span
            className={
              s.done
                ? "font-medium text-zinc-900 dark:text-zinc-100"
                : "text-zinc-500 dark:text-zinc-400"
            }
          >
            {s.label}
          </span>
          <span className="sr-only">{s.done ? "(concluída)" : "(pendente)"}</span>
        </li>
      ))}
    </ul>
  );
}
'''


def l4_04(E):
    ep = E("L4", "l4-04-delivery-steps", setup={"files": {"components/DeliverySteps.tsx": DELIVERY_POOR}})
    ep.user("as etapas de entrega do pedido tão feias e confusas — 'ok' e traço?? deixa isso digno")
    ep.act(
        "Vamos ver o tamanho da indignidade antes de listar o conserto:",
        "read_file", expect=r"DeliverySteps", path="components/DeliverySteps.tsx")
    ep.act(
        "Entendo a revolta: o estado da etapa é um \"ok\"/\"-\" textual, sem espaçamento, sem "
        "hierarquia, sem dark mode. Auditoria completa — 5 correções num edit só:\n"
        "1. indicador visual de verdade: círculo verde com check pra concluída, círculo vazio "
        "com borda pra pendente (semântica de cor + forma, não texto solto);\n"
        "2. hierarquia: etapa concluída em cor plena + font-medium, pendente rebaixada;\n"
        "3. espaçamento: space-y-3 entre etapas, gap-3 entre círculo e rótulo;\n"
        "4. dark mode nos dois estados;\n"
        "5. acessibilidade: o círculo é decorativo (aria-hidden) e o estado vai num sr-only "
        "textual — leitor de tela ouve \"(concluída)\", não emoji.\n"
        "Reescrevendo:",
        "write_file", expect=r"ok:", path="components/DeliverySteps.tsx", content=DELIVERY_GOOD)
    ep.verify_green(
        "Etapas dignificadas. Typecheck:")
    ep.final(
        "DeliverySteps reformado num passe: o \"ok\"/\"-\" virou indicador visual de verdade — "
        "círculo verde com check nas concluídas, círculo vazio nas pendentes — com hierarquia "
        "tipográfica (concluída em cor plena, pendente rebaixada), respiro entre etapas, dark "
        "mode completo e acessibilidade correta (círculo decorativo em aria-hidden, estado "
        "narrado via sr-only). Compilando limpo.")
    return ep


PLAN_POOR = '''type Plan = { name: string; price: string };

export default function PlanSelector({ plans, selected, onSelect }: {
  plans: Plan[];
  selected: string;
  onSelect: (name: string) => void;
}) {
  return (
    <div className="flex gap-2">
      {plans.map((p) => (
        <button key={p.name} onClick={() => onSelect(p.name)} className="border p-2">
          <div>{p.name}</div>
          <div>{p.price}</div>
        </button>
      ))}
    </div>
  );
}
'''

PLAN_GOOD = '''"use client";

import { cn } from "@/lib/utils";

type Plan = { name: string; price: string };

export default function PlanSelector({ plans, selected, onSelect }: {
  plans: Plan[];
  selected: string;
  onSelect: (name: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3" role="radiogroup" aria-label="Escolha um plano">
      {plans.map((p) => {
        const isSelected = p.name === selected;
        return (
          <button
            key={p.name}
            type="button"
            role="radio"
            aria-checked={isSelected}
            onClick={() => onSelect(p.name)}
            className={cn(
              "rounded-2xl border p-4 text-left transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-zinc-950",
              isSelected
                ? "border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                : "border-zinc-200 bg-white hover:border-zinc-400 dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-zinc-600",
            )}
          >
            <div className="text-sm font-semibold tracking-tight">{p.name}</div>
            <div className={cn("mt-1 text-sm", isSelected ? "opacity-80" : "text-zinc-500 dark:text-zinc-400")}>
              {p.price}
            </div>
          </button>
        );
      })}
    </div>
  );
}
'''


def l4_05(E):
    ep = E("L4", "l4-05-plan-selector", setup={"files": {"components/PlanSelector.tsx": PLAN_POOR}})
    ep.user("o seletor de planos do onboarding tá um esqueleto sem estilo — e nem dá pra saber qual plano tá selecionado. conserta inteiro, por favor")
    ep.act(
        "\"Nem dá pra saber qual tá selecionado\" é a pista principal: além do visual cru, o "
        "componente recebe `selected` e não usa. Lendo pra auditar tudo:",
        "read_file", expect=r"PlanSelector", path="components/PlanSelector.tsx")
    ep.act(
        "Confirmado — a prop `selected` chega e é ignorada, e o resto acompanha: sem estado "
        "visual, sem foco, sem dark, sem responsividade. Auditoria completa, tudo num edit:\n"
        "1. o bug funcional: plano selecionado ganha inversão de cor (fundo escuro no claro, "
        "claro no escuro) — impossível não ver;\n"
        "2. semântica de grupo: isso é uma escolha exclusiva → role=\"radiogroup\" com cada "
        "cartão role=\"radio\" + aria-checked;\n"
        "3. \"use client\" que faltava (tem onClick — ia quebrar o build);\n"
        "4. grid responsivo (1 coluna no mobile, 3 no desktop) no lugar do flex apertado;\n"
        "5. superfície do guia: rounded-2xl, borda com hover, transição, focus-visible:ring;\n"
        "6. hierarquia: nome em semibold, preço rebaixado.\n"
        "Reescrevendo:",
        "write_file", expect=r"ok:", path="components/PlanSelector.tsx", content=PLAN_GOOD)
    ep.verify_green(
        "Seletor reconstruído. Typecheck — inclusive pro cn() que introduzi:")
    ep.final(
        "PlanSelector reconstruído de uma vez: o bug real era a prop `selected` ignorada — "
        "agora o plano escolhido inverte as cores e é óbvio nos dois temas. Junto foram: "
        "semântica de radiogroup/radio com aria-checked (é escolha exclusiva, leitor de tela "
        "agradece), o `\"use client\"` que faltava pro onClick, grid responsivo 1→3 colunas, "
        "superfícies no padrão (rounded-2xl, hover na borda, transição, focus ring) e "
        "hierarquia nome/preço. Compilou limpo.")
    return ep


USAGE_POOR = '''export default function UsageMeter({ used, limit }: { used: number; limit: number }) {
  const pct = Math.round((used / limit) * 100);
  return (
    <div>
      <div className="text-sm">Storage: {pct}%</div>
      <div className="h-2 w-full bg-zinc-200">
        <div className="h-2 bg-zinc-900" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
'''

USAGE_GOOD = '''export default function UsageMeter({ used, limit }: { used: number; limit: number }) {
  const pct = Math.min(100, Math.round((used / limit) * 100));
  const tone =
    pct >= 90
      ? "bg-rose-500"
      : pct >= 70
        ? "bg-amber-500"
        : "bg-emerald-500";
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-medium">Storage</span>
        <span className="tabular-nums text-zinc-500 dark:text-zinc-400">
          {used} / {limit} GB · {pct}%
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Uso de armazenamento: ${pct}%`}
        className="h-2 w-full overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-300 ${tone}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
'''


def l4_06(E):
    ep = E("L4", "l4-06-usage-meter-en", lang="en",
           setup={"files": {"components/UsageMeter.tsx": USAGE_POOR}})
    ep.user("our storage usage meter looks like a 2005 loading bar — make it match the app, and it should probably warn people near the limit?")
    ep.act(
        "Let me read the current bar to audit it fully — you already spotted the missing "
        "warning states, let's see what else is hiding:",
        "read_file", expect=r"UsageMeter", path="components/UsageMeter.tsx")
    ep.act(
        "Full audit — six fixes in one rewrite:\n"
        "1. the ask: threshold tones — green below 70%, amber to 89%, rose at 90%+ (semantic "
        "color doing the warning work);\n"
        "2. unclamped math: used > limit renders a bar past 100% — clamp it;\n"
        "3. square everything → rounded-full track with overflow-hidden so the fill respects "
        "the radius;\n"
        "4. no dark mode on the track → dark:bg-zinc-800;\n"
        "5. no a11y: this is a progressbar → role + aria-valuenow/min/max + label;\n"
        "6. label line upgraded: name in medium weight, \"used / limit GB · %\" right-aligned "
        "in tabular-nums, plus a width transition so updates glide instead of jumping.\n"
        "Writing it:",
        "write_file", expect=r"ok:", path="components/UsageMeter.tsx", content=USAGE_GOOD)
    ep.verify_green(
        "Rewritten. Typecheck before handing it back:")
    ep.final(
        "UsageMeter modernized in one pass: threshold tones as requested (green → amber at "
        "70% → rose at 90%), clamped percentage so overuse can't overflow the bar, rounded "
        "track with proper dark mode, full progressbar a11y (role + aria values + label), a "
        "richer label line (used / limit GB · % in tabular-nums) and a smooth width "
        "transition. Typecheck is green.")
    return ep


# ============================================================ L5 — recuperação de tool call

def l5_04(E):
    ep = E("L5", "l5-04-path-errado")
    ep.user("adiciona um link 'Blog' na navegação principal, apontando pra /blog")
    ep.act(
        "Navegação principal — vou ler o componente de header pra ver a estrutura dos links. "
        "Pelo padrão de nomes, HeaderNav:",
        "read_file", expect=r"Erro: arquivo não encontrado", path="components/HeaderNav.tsx")
    ep.act(
        "Não existe HeaderNav — chutei o nome e o projeto me corrigiu. Neste template a "
        "navegação é o Navbar (lembro dele na estrutura). Lendo o arquivo certo:",
        "read_file", expect=r"const links", path="components/Navbar.tsx")
    ep.act(
        "Achei: os links vivem no array `links` no topo do Navbar.tsx — é só acrescentar a "
        "entrada do Blog na lista, que o map renderiza com o estilo já existente:",
        "edit_file", expect=r"ok:", path="components/Navbar.tsx",
        old='  { label: "Preços", href: "#precos" },\n];',
        new='  { label: "Preços", href: "#precos" },\n  { label: "Blog", href: "/blog" },\n];')
    ep.verify_green(
        "Link adicionado ao array. Typecheck de rotina:")
    ep.final(
        "Link \"Blog\" → `/blog` adicionado à navegação. Nota do caminho: tentei "
        "`HeaderNav.tsx` primeiro (não existia), o erro me corrigiu e fui pro "
        "`components/Navbar.tsx`, onde os links são um array no topo do arquivo — acrescentei "
        "a entrada e o map existente cuida do estilo e do hover. Typecheck verde.")
    return ep


HELP_LINK = '''import Link from "next/link";

export default function HelpLink() {
  return (
    <Link
      href="/ajuda"
      className="text-sm text-zinc-600 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
    >
      Precisa de ajuda?
    </Link>
  );
}
'''


def l5_05(E):
    ep = E("L5", "l5-05-edit-reancorado", setup={"files": {"components/HelpLink.tsx": HELP_LINK}})
    ep.user("troca o texto do HelpLink de 'Precisa de ajuda?' pra 'Central de ajuda' e faz ele abrir em /central-de-ajuda")
    ep.act(
        "Duas mudanças no mesmo componente — texto e href. Edito os dois de uma vez pelo "
        "trecho que envolve ambos:",
        "edit_file", expect=r"não encontrado",
        path="components/HelpLink.tsx",
        old='<Link href="/ajuda" className="text-sm text-zinc-600',
        new='<Link href="/central-de-ajuda" className="text-sm text-zinc-600')
    ep.act(
        "O edit não casou — escrevi o trecho de memória e a formatação real deve ser "
        "diferente (quebras de linha, provavelmente). Regra: quando o `old` falha, NÃO "
        "adivinhar de novo — reler o arquivo e copiar o trecho exato:",
        "read_file", expect=r'href="/ajuda"', path="components/HelpLink.tsx")
    ep.act(
        "Agora vejo: o `href` está numa linha própria (o componente é multi-linha, não "
        "inline como assumi). Com o texto exato em mãos, edito o href:",
        "edit_file", expect=r"ok:", path="components/HelpLink.tsx",
        old='      href="/ajuda"', new='      href="/central-de-ajuda"')
    ep.act(
        "E o texto do link:",
        "edit_file", expect=r"ok:", path="components/HelpLink.tsx",
        old="      Precisa de ajuda?", new="      Central de ajuda")
    ep.verify_green(
        "As duas mudanças aplicadas. Typecheck:")
    ep.final(
        "Feito: o HelpLink agora diz \"Central de ajuda\" e aponta pra `/central-de-ajuda`. "
        "Registro honesto do caminho: meu primeiro edit falhou porque escrevi o trecho de "
        "memória assumindo o JSX inline — em vez de chutar de novo, reli o arquivo, vi que o "
        "href fica em linha própria e ancorei os edits no texto exato. Typecheck verde.")
    return ep


def l5_06(E):
    ep = E("L5", "l5-06-curl-blocked-en", lang="en")
    ep.user("before I add zod to the project, can you check what the latest version is?")
    ep.act(
        "Quick registry lookup. First instinct is hitting the registry API directly:",
        "run_terminal", expect=r"não permitido", command="curl -s https://registry.npmjs.org/zod/latest")
    ep.act(
        "curl isn't on this terminal's allowlist — fair enough, npm itself answers this "
        "natively and it IS allowed. `npm view` queries the registry without installing "
        "anything:",
        "run_terminal", expect=r"\[exit 0\]", command="npm view zod version")
    ep.final(
        "Got it via `npm view zod version` (curl is blocked on this terminal's allowlist, but "
        "npm queries the registry natively — no install involved). The output above shows the "
        "current latest on the npm registry. If you want, I can also check `npm view zod "
        "dist-tags` to see if there's a beta/next channel before you commit to a version.")
    return ep


# ============================================================ LC — conversa técnica

def lc_05(E):
    ep = E("LC", "lc-05-fontes-lighthouse")
    ep.user("meu score de performance no lighthouse despencou depois que adicionei duas fontes customizadas. isso é normal? tem salvação?")
    ep.final(
        "É normal, tem salvação, e o mecanismo é conhecido: fonte customizada mal carregada "
        "ataca o Lighthouse por dois flancos ao mesmo tempo. Primeiro o **texto invisível ou "
        "piscando** (FOIT/FOUT): o navegador segura ou troca o texto quando a fonte chega, o "
        "que infla o LCP se o seu elemento principal é texto — e quase sempre é. Segundo o "
        "**layout shift**: a fonte de fallback tem métricas diferentes da customizada, então "
        "quando a troca acontece o texto reflui e o CLS pontua contra você.\n\n"
        "A salvação, em ordem de impacto:\n"
        "1. **`next/font`** (se está no Next, é a resposta quase completa): ele hospeda a "
        "fonte localmente (elimina a viagem até o Google Fonts), aplica `font-display` "
        "sensato e — a parte subestimada — calcula um fallback com métricas ajustadas "
        "(`adjustFontFallback`), o que mata o CLS da troca.\n"
        "2. **Subsetting**: se você usa duas famílias completas com todos os pesos, está "
        "baixando dezenas de variações pra usar quatro. Carrega só os pesos que o design usa "
        "(ex.: 400 e 700) e o subset latin.\n"
        "3. **Uma fonte a menos**: pergunta honesta de design — a segunda família paga o "
        "custo? Muitas vezes um peso diferente da primeira resolve a mesma hierarquia.\n\n"
        "Com `next/font` + subset de dois pesos, é comum recuperar quase todo o score "
        "perdido. Se depois disso ainda estiver ruim, o problema é outro e vale olhar o "
        "restante do relatório — fonte vira bode expiatório fácil.")
    return ep


def lc_06(E):
    ep = E("LC", "lc-06-explicar-rsc")
    ep.user("Preciso explicar server components pro meu júnior amanhã e não quero enrolar. Como você explicaria?")
    ep.final(
        "Explicaria em três atos, do concreto pro abstrato — júnior aprende melhor vendo o "
        "problema antes da solução:\n\n"
        "**Ato 1 — o problema.** Mostra um componente clássico que busca dados: useEffect + "
        "useState + loading + fetch. Aí pergunta: \"por que o navegador precisa receber o "
        "CÓDIGO dessa busca, executar, esperar a resposta e só então mostrar o conteúdo?\" O "
        "usuário baixou JavaScript pra construir uma tela que o servidor já sabia montar.\n\n"
        "**Ato 2 — a ideia.** Server component é isso: o componente roda NO servidor, pode "
        "ser `async` e fazer `await` da busca direto no corpo, e o que viaja pro navegador é "
        "o resultado renderizado — não o código. Menos JS baixado, dado buscado perto da "
        "fonte, zero loading state artificial. O exemplo do Ato 1 reescrito encolhe de ~30 "
        "linhas pra ~8, e isso impressiona mais que qualquer slide.\n\n"
        "**Ato 3 — a regra prática.** Quando cada um: começa tudo como server (é o default do "
        "App Router); no momento em que o componente precisa de estado, efeito ou evento "
        "(clicar, digitar), ele vira client com `\"use client\"` no topo. A arquitetura "
        "saudável fica: páginas e seções são server, e as FOLHAS interativas (botão, form, "
        "menu) são client.\n\n"
        "Duas armadilhas pra avisar de antemão, porque ele VAI cair nelas: (1) \"use client\" "
        "não significa \"roda só no cliente\" — client components ainda renderizam no "
        "servidor na primeira carga; (2) props de server pra client precisam ser "
        "serializáveis — função não passa. Se sobrar tempo, deixa ele quebrar o build ao "
        "vivo com um useState sem diretiva: o erro que ele mesmo provocou ensina mais que a "
        "tua explicação inteira.")
    return ep


def lc_07(E):
    ep = E("LC", "lc-07-tabs-vs-accordion-en", lang="en")
    ep.user("settings page on mobile: tabs or accordion? design team is split")
    ep.final(
        "I'd side with the accordion for mobile settings, and here's the reasoning your "
        "design team can argue about concretely.\n\n"
        "**Why tabs struggle on mobile settings:** tabs assume the labels fit in a row — "
        "settings categories rarely do (\"Notifications\", \"Privacy & Security\", "
        "\"Billing\"...), so you end up with horizontally scrollable tabs, which hide "
        "options off-screen and are the least discoverable navigation pattern on touch. "
        "Tabs also imply the user switches contexts often; in settings they typically dive "
        "into ONE section, change a thing, and leave.\n\n"
        "**Why accordion fits:** everything is visible as a scannable vertical list (mobile "
        "users scroll naturally, they don't swipe sideways), multiple sections can be open "
        "when someone's comparing related options, and deep-linking to an expanded section "
        "for support flows (\"tap here to open notification settings\") works cleanly.\n\n"
        "**The caveat that matters:** if each section is HEAVY (long forms), a full-page "
        "drill-down per section — the iOS Settings model, a simple list where each row "
        "pushes a new screen — beats both. That's really an accordion whose panels grew up.\n\n"
        "So the split I'd propose to the team: few sections with short content → accordion; "
        "long forms per section → list + drill-down pages; tabs only if you have 2-3 "
        "sections with genuinely short labels that will never grow. Settings pages always "
        "grow.")
    return ep


EPISODES = [
    l1_05, l1_06, l1_07, l1_08,
    l2_04, l2_05, l2_06, l2_07,
    l3_04, l3_05, l3_06,
    l4_04, l4_05, l4_06,
    l5_04, l5_05, l5_06,
    lc_05, lc_06, lc_07,
]
