"""Gera eidos/eval_cases.jsonl — os 100 casos da Fase 0.

Famílias:
    fix-build (30)        erro plantado -> métrica: tsc/build volta a passar
    fix-visual (20)       bug visual descrito -> métrica: tsc + padrão aceito no arquivo
    create-component (30) componente novo no guia de estilo -> métrica: existe + tsc + asserts
    terminal-ops (20)     ação via terminal -> métrica: dep/arquivo/comando + tsc

Checks disponíveis (executados por run_eval.py):
    {"type": "tsc"}                                  npx tsc --noEmit == exit 0
    {"type": "build"}                                npm run build == exit 0 (caro; só quando tsc não pega)
    {"type": "file_exists", "path": ...}
    {"type": "file_contains", "path": ..., "pattern": <regex>}
    {"type": "file_not_contains", "path": ..., "pattern": <regex>}
    {"type": "package_dep", "name": ...}             em dependencies OU devDependencies
    {"type": "package_script", "name": ...}
    {"type": "ran_command", "pattern": <regex>}      algum run_terminal do episódio casa
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "eval_cases.jsonl"
cases = []


def case(id, family, prompt, checks, setup=None, max_iters=6):
    cases.append({"id": id, "family": family, "prompt": prompt,
                  "setup": setup or {}, "checks": checks, "max_iters": max_iters})


# ============================================================ fix-build (30)
FB = "fix-build"

case("fb-001", FB,
     "O build parou de passar depois que mexeram no Button. Roda o build, descobre o que é e conserta.",
     [{"type": "build"}],
     setup={"files": {"components/Button.tsx": '''import { useState } from "react";
import { cn } from "@/lib/utils";

type ButtonProps = {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

const variants = {
  primary:
    "bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300",
  secondary:
    "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800",
  ghost:
    "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-100",
};

const sizes = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-11 px-6 text-base",
};

export default function Button({
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  const [pressed, setPressed] = useState(false);
  return (
    <button
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium",
        "transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-zinc-950",
        "disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        pressed && "scale-95",
        className,
      )}
      {...props}
    />
  );
}
'''}})

case("fb-002", FB,
     "Tô vendo erro de tipo no Card.tsx. Verifica com o typecheck e arruma.",
     [{"type": "tsc"}],
     setup={"files": {"components/Card.tsx": '''import { cn } from "lib/utils";

type CardProps = {
  title?: string;
  children?: React.ReactNode;
  className?: string;
};

export default function Card({ title, children, className }: CardProps) {
  return (
    <div className={cn("rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900", className)}>
      {title ? <h3 className="text-base font-semibold tracking-tight">{title}</h3> : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}
'''}})

case("fb-003", FB,
     "O typecheck quebrou na página inicial. Investiga e corrige.",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import Card from "@/components/Card";

export default function Home() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-24">
      <Card title="Bem-vindo" description="Página inicial do template">
        <p className="text-sm text-zinc-500">Conteúdo do card.
      </Card>
    </main>
  );
}
'''}})

case("fb-004", FB,
     "Alguém apagou o lib/utils.ts sem querer e agora nada compila. Recria o helper cn e confirma que o typecheck volta a passar.",
     [{"type": "file_exists", "path": "lib/utils.ts"}, {"type": "tsc"}],
     setup={"delete": ["lib/utils.ts"]})

case("fb-005", FB,
     "O Navbar está com erro de compilação. Dá uma olhada e conserta.",
     [{"type": "tsc"}],
     setup={"files": {"components/Navbar.tsx": '''import Link from "next/link";

const links = [
  { label: "Início", href: "/" },
  { label: "Preços", href: "#precos" },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">eidos</Link>
        <ul className="flex items-center gap-6">
          {navLinks.map((link) => (
            <li key={link.href}>
              <Link href={link.href} className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </header>
  );
}
'''}})

case("fb-006", FB,
     "O Button está dando erro de tipo no valor default da prop variant. Corrige mantendo o comportamento.",
     [{"type": "tsc"}],
     setup={"files": {"components/Button.tsx": '''import { cn } from "@/lib/utils";

type ButtonProps = {
  variant?: "primary" | "secondary" | "ghost";
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

export default function Button({ variant = "solid", className, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-xl px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500",
        variant === "primary" && "bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900",
        variant === "secondary" && "border border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800",
        variant === "ghost" && "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800",
        className,
      )}
      {...props}
    />
  );
}
'''}})

case("fb-007", FB,
     "A home quebrou com erro de import. Resolve.",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import { Button } from "@/components/Button";

export default function Home() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 py-24">
      <h1 className="text-4xl font-bold tracking-tight">Template Eidos</h1>
      <Button>Começar</Button>
    </main>
  );
}
'''}})

case("fb-008", FB,
     "O build está falhando com erro de CSS. Encontra e corrige.",
     [{"type": "build"}],
     setup={"files": {"app/globals.css": '''@tailwind bases;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-zinc-50 text-zinc-900 antialiased dark:bg-zinc-950 dark:text-zinc-100;
  }
}
'''}})

case("fb-009", FB,
     "Mexeram no tailwind.config.ts e o typecheck não passa mais. Conserta.",
     [{"type": "tsc"}],
     setup={"files": {"tailwind.config.ts": '''import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  plugins: [],
};

export default config;
'''}})

case("fb-010", FB,
     "Todos os imports com @/ pararam de resolver de uma vez. Descobre a causa raiz e corrige (sem reescrever os imports um a um).",
     [{"type": "tsc"}],
     setup={"files": {"tsconfig.json": '''{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
'''}})

case("fb-011", FB,
     "O Card dá erro dizendo que children não existe nas props. Arruma a tipagem.",
     [{"type": "tsc"}],
     setup={"files": {"components/Card.tsx": '''import { cn } from "@/lib/utils";

type CardProps = {
  title?: string;
  className?: string;
};

export default function Card({ title, children, className }: CardProps) {
  return (
    <div className={cn("rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900", className)}>
      {title ? <h3 className="text-base font-semibold tracking-tight">{title}</h3> : null}
      <div className="mt-4">{children}</div>
    </div>
  );
}
'''}})

case("fb-012", FB,
     "Erro de tipo na lista de estatísticas da home. Verifica e corrige.",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''export default function Home() {
  const visitas: number[] = ["1200", "3400", "5100"];
  return (
    <main className="mx-auto max-w-6xl px-4 py-24">
      <h1 className="text-4xl font-bold tracking-tight">Visitas</h1>
      <ul className="mt-6 flex gap-4">
        {visitas.map((v) => (
          <li key={v} className="rounded-xl border border-zinc-200 px-4 py-2 text-sm dark:border-zinc-800">
            {v}
          </li>
        ))}
      </ul>
    </main>
  );
}
'''}})

case("fb-013", FB,
     "O Navbar novo usa useEffect mas não compila. Conserta.",
     [{"type": "tsc"}],
     setup={"files": {"components/Navbar.tsx": '''"use client";

import Link from "next/link";
import { useState } from "react";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={scrolled ? "border-b border-zinc-200 dark:border-zinc-800" : ""}>
      <nav className="mx-auto flex h-16 max-w-6xl items-center px-4">
        <Link href="/" className="text-sm font-semibold tracking-tight">eidos</Link>
      </nav>
    </header>
  );
}
'''}})

case("fb-014", FB,
     "O helper de formatação em lib/utils.ts está com erro de tipo de retorno. Corrige.",
     [{"type": "tsc"}],
     setup={"files": {"lib/utils.ts": '''export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}

export function formatPercent(value: number): string {
  if (value > 0) {
    return `+${value.toFixed(1)}%`;
  }
  if (value < 0) {
    return `${value.toFixed(1)}%`;
  }
}
'''}})

case("fb-015", FB,
     "Deu conflito de merge mal resolvido no Button e agora tem código duplicado que não compila. Limpa.",
     [{"type": "tsc"}],
     setup={"files": {"components/Button.tsx": '''import { cn } from "@/lib/utils";

export default function Button({ className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn("inline-flex h-10 items-center justify-center rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900", className)}
      {...props}
    />
  );
}

export default function Button({ className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={className} {...props} />;
}
'''}})

case("fb-016", FB,
     "A página de perfil não compila por causa de um import. Resolve.",
     [{"type": "tsc"}],
     setup={"files": {"app/perfil/page.tsx": '''import Image from "next/imag";

export default function Perfil() {
  return (
    <main className="mx-auto max-w-2xl px-4 py-24">
      <Image src="/avatar.png" alt="Avatar do usuário" width={96} height={96} className="rounded-full" />
      <h1 className="mt-6 text-2xl font-bold tracking-tight">Perfil</h1>
    </main>
  );
}
'''}})

case("fb-017", FB,
     "O handler de clique do componente de copiar está com tipo errado. Conserta.",
     [{"type": "tsc"}],
     setup={"files": {"components/CopyButton.tsx": '''"use client";

export default function CopyButton({ text }: { text: string }) {
  const handleClick = (valor: number) => {
    navigator.clipboard.writeText(valor);
  };

  return (
    <button
      onClick={handleClick}
      className="rounded-xl border border-zinc-300 px-3 py-1.5 text-sm transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
      aria-label="Copiar texto"
    >
      Copiar
    </button>
  );
}
'''}})

case("fb-018", FB,
     "Um componente veio de HTML puro e não compila em TSX. Corrige.",
     [{"type": "tsc"}],
     setup={"files": {"components/Tag.tsx": '''export default function Tag({ label }: { label: string }) {
  return (
    <span class="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
      {label}
    </span>
  );
}
'''}})

case("fb-019", FB,
     "A home está passando prop com tipo errado pro Card. Verifica o erro e corrige.",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import Card from "@/components/Card";

export default function Home() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-24">
      <Card title={42} description="Total de usuários ativos" />
    </main>
  );
}
'''}})

case("fb-020", FB,
     "O lib/utils.ts está com erro de sintaxe. Conserta.",
     [{"type": "tsc"}],
     setup={"files": {"lib/utils.ts": '''export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");

export function slugify(text: string): string {
  return text.toLowerCase().replace(/\\s+/g, "-");
}
'''}})

case("fb-021", FB,
     "O build falha reclamando do usePathname no Navbar, mas o typecheck passa. Roda o build, entende o erro do Next e corrige.",
     [{"type": "build"}],
     setup={"files": {"components/Navbar.tsx": '''import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { label: "Início", href: "/" },
  { label: "Preços", href: "/precos" },
];

export default function Navbar() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-4">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              "text-sm transition-colors hover:text-zinc-900 dark:hover:text-zinc-100",
              pathname === link.href ? "font-semibold text-zinc-900 dark:text-zinc-100" : "text-zinc-600 dark:text-zinc-400",
            )}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
'''}})

case("fb-022", FB,
     "O import do Card na home está com problema de resolução de módulo. Corrige.",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import Card from "@/components/card";

export default function Home() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-24">
      <Card title="Bem-vindo" description="Página inicial" />
    </main>
  );
}
'''}})

case("fb-023", FB,
     "A home passa uma prop que o Button não aceita e o typecheck reclama. Resolve do jeito certo (botão de link é link).",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import Button from "@/components/Button";

export default function Home() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 py-24">
      <h1 className="text-4xl font-bold tracking-tight">Template Eidos</h1>
      <Button href="/docs">Ver documentação</Button>
    </main>
  );
}
'''}})

case("fb-024", FB,
     "Tem um fragment mal fechado num componente novo. Conserta a sintaxe.",
     [{"type": "tsc"}],
     setup={"files": {"components/Stat.tsx": '''export default function Stat({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-sm text-zinc-500 dark:text-zinc-400">{label}</dt>
      <dd className="text-2xl font-bold tracking-tight">{value}</dd>
  );
}
'''}})

case("fb-025", FB,
     "O build falha dizendo que a página não tem um componente React válido como default export. Corrige.",
     [{"type": "build"}],
     setup={"files": {"app/page.tsx": '''export function Home() {
  return (
    <main className="mx-auto max-w-6xl px-4 py-24">
      <h1 className="text-4xl font-bold tracking-tight">Template Eidos</h1>
    </main>
  );
}
'''}})

case("fb-026", FB,
     "O layout está usando um import type como valor e não compila. Arruma.",
     [{"type": "tsc"}],
     setup={"files": {"app/layout.tsx": '''import type { Metadata } from "next";
import "./globals.css";

export const metadata = Metadata({
  title: "Eidos Template",
  description: "Base app",
});

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
'''}})

case("fb-027", FB,
     "A home usa um tamanho de botão que não existe no tipo. Alinha os dois lados (decide se cria o tamanho ou troca o uso).",
     [{"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import Button from "@/components/Button";

export default function Home() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-4 py-24">
      <h1 className="text-4xl font-bold tracking-tight">Template Eidos</h1>
      <Button size="xl">Começar agora</Button>
    </main>
  );
}
'''}})

case("fb-028", FB,
     "A home importa formatCurrency de @/lib/format, mas o arquivo não existe ainda. Cria o helper (formata número pra BRL) e faz compilar.",
     [{"type": "file_exists", "path": "lib/format.ts"}, {"type": "tsc"}],
     setup={"files": {"app/page.tsx": '''import { formatCurrency } from "@/lib/format";

export default function Home() {
  const receita = 184200.5;
  return (
    <main className="mx-auto max-w-6xl px-4 py-24">
      <h1 className="text-4xl font-bold tracking-tight">Receita do mês</h1>
      <p className="mt-4 text-2xl font-semibold">{formatCurrency(receita)}</p>
    </main>
  );
}
'''}})

case("fb-029", FB,
     "Erro bobo de digitação nas props de um componente novo está quebrando o typecheck. Encontra e corrige.",
     [{"type": "tsc"}],
     setup={"files": {"components/SectionHeading.tsx": '''export default function SectionHeading({ titel, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="space-y-1">
      <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
      {subtitle ? <p className="text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p> : null}
    </div>
  );
}
'''}})

case("fb-030", FB,
     "O metadata do layout está com tipo errado. Corrige usando o tipo do Next.",
     [{"type": "tsc"}],
     setup={"files": {"app/layout.tsx": '''import type { Metadata } from "next";
import "./globals.css";

export const metadata: string = {
  title: "Eidos Template",
  description: "Base app",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
'''}})

# ============================================================ fix-visual (20)
FV = "fix-visual"

case("fv-001", FV,
     "O botão em components/PlainButton.tsx parece morto: nada acontece no hover nem no foco por teclado. Deixa ele vivo, seguindo o guia de estilo.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/PlainButton.tsx", "pattern": "hover:"},
      {"type": "file_contains", "path": "components/PlainButton.tsx", "pattern": "focus-visible:|focus:"},
      {"type": "file_contains", "path": "components/PlainButton.tsx", "pattern": "transition"}],
     setup={"files": {"components/PlainButton.tsx": '''export default function PlainButton({ children }: { children: React.ReactNode }) {
  return (
    <button className="inline-flex h-10 items-center justify-center rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white">
      {children}
    </button>
  );
}
'''}})

case("fv-002", FV,
     "O components/LightCard.tsx fica ilegível quando o tema escuro está ativo (fundo branco fixo). Adiciona suporte a dark mode.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/LightCard.tsx", "pattern": "dark:"}],
     setup={"files": {"components/LightCard.tsx": '''export default function LightCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
      <h3 className="text-base font-semibold tracking-tight text-zinc-900">{title}</h3>
      <p className="mt-1 text-sm text-zinc-500">{body}</p>
    </div>
  );
}
'''}})

case("fv-003", FV,
     "Na seção hero de components/Hero.tsx está tudo colado: título, texto e botões sem respiro nenhum. Dá espaçamento decente.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/Hero.tsx", "pattern": "gap-|space-y-|mt-|mb-"}],
     setup={"files": {"components/Hero.tsx": '''export default function Hero() {
  return (
    <section className="flex flex-col items-center py-24 text-center">
      <h1 className="text-4xl font-bold tracking-tight">Construa mais rápido</h1>
      <p className="text-lg text-zinc-500 dark:text-zinc-400">Componentes prontos pro seu próximo projeto.</p>
      <div className="flex">
        <button className="rounded-xl bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900">Começar</button>
        <button className="rounded-xl border border-zinc-300 px-4 py-2 text-sm dark:border-zinc-700">Saiba mais</button>
      </div>
    </section>
  );
}
'''}})

case("fv-004", FV,
     "O components/WideNav.tsx estoura no mobile: os links não cabem e causam scroll horizontal. Torna responsivo (pode esconder links no mobile).",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/WideNav.tsx", "pattern": "sm:|md:|lg:|flex-wrap"}],
     setup={"files": {"components/WideNav.tsx": '''import Link from "next/link";

const links = ["Produto", "Soluções", "Preços", "Documentação", "Blog", "Contato"];

export default function WideNav() {
  return (
    <nav className="flex h-16 items-center gap-8 border-b border-zinc-200 px-4 dark:border-zinc-800">
      <span className="text-sm font-semibold tracking-tight">eidos</span>
      <ul className="flex items-center gap-8">
        {links.map((l) => (
          <li key={l}>
            <Link href="#" className="whitespace-nowrap text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
              {l}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
'''}})

case("fv-005", FV,
     "A foto do components/ProfileHeader.tsx aparece esticada/distorcida. Corrige o enquadramento da imagem.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/ProfileHeader.tsx", "pattern": "object-cover|aspect-|rounded-full"}],
     setup={"files": {"components/ProfileHeader.tsx": '''export default function ProfileHeader({ name, avatarUrl }: { name: string; avatarUrl: string }) {
  return (
    <div className="flex items-center gap-4">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={avatarUrl} alt={`Foto de ${name}`} className="h-16 w-24" />
      <h2 className="text-xl font-semibold tracking-tight">{name}</h2>
    </div>
  );
}
'''}})

case("fv-006", FV,
     "O texto do components/Announcement.tsx está com contraste baixo demais (cinza claro em fundo claro), quase ilegível. Corrige as cores mantendo a hierarquia.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/Announcement.tsx", "pattern": "text-zinc-[6789]00|text-zinc-950"}],
     setup={"files": {"components/Announcement.tsx": '''export default function Announcement() {
  return (
    <div className="rounded-2xl border border-zinc-200 bg-zinc-100 p-6 dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-base font-semibold text-zinc-300">Nova versão disponível</h3>
      <p className="mt-1 text-sm text-zinc-200">A versão 2.0 traz componentes novos e melhorias de acessibilidade.</p>
    </div>
  );
}
'''}})

case("fv-007", FV,
     "O botão de fechar do components/Banner.tsx é só um X sem nome acessível: leitor de tela anuncia 'botão'. Corrige a acessibilidade.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/Banner.tsx", "pattern": "aria-label"}],
     setup={"files": {"components/Banner.tsx": '''"use client";

import { useState } from "react";

export default function Banner() {
  const [open, setOpen] = useState(true);
  if (!open) return null;
  return (
    <div className="flex items-center justify-between rounded-xl bg-zinc-900 px-4 py-3 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900">
      <span>Frete grátis em pedidos acima de R$ 200.</span>
      <button onClick={() => setOpen(false)} className="rounded-lg p-1 transition-colors hover:bg-white/10 dark:hover:bg-zinc-900/10">
        ×
      </button>
    </div>
  );
}
'''}})

case("fv-008", FV,
     "O components/FloatingPanel.tsx parece um retângulo solto na página, sem definição nenhuma contra o fundo. Dá definição de superfície (guia de estilo).",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/FloatingPanel.tsx", "pattern": "border|shadow|ring"}],
     setup={"files": {"components/FloatingPanel.tsx": '''export default function FloatingPanel({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl bg-white p-6 dark:bg-zinc-900">
      {children}
    </div>
  );
}
'''}})

case("fv-009", FV,
     "O components/StatsRow.tsx mostra as métricas empilhadas numa coluna única mesmo em tela grande, desperdiçando espaço. Vira grid responsivo.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/StatsRow.tsx", "pattern": "grid-cols-2|grid-cols-3|grid-cols-4|sm:grid|lg:grid"}],
     setup={"files": {"components/StatsRow.tsx": '''const stats = [
  { label: "Usuários", value: "12.4k" },
  { label: "Receita", value: "R$ 84k" },
  { label: "Conversão", value: "3,2%" },
];

export default function StatsRow() {
  return (
    <dl className="flex flex-col gap-4">
      {stats.map((s) => (
        <div key={s.label} className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <dt className="text-sm text-zinc-500 dark:text-zinc-400">{s.label}</dt>
          <dd className="mt-1 text-2xl font-bold tracking-tight">{s.value}</dd>
        </div>
      ))}
    </dl>
  );
}
'''}})

case("fv-010", FV,
     "Títulos longos quebram o layout do components/ArticleCard.tsx (transbordam do card). Trata o overflow do texto.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/ArticleCard.tsx", "pattern": "truncate|line-clamp"}],
     setup={"files": {"components/ArticleCard.tsx": '''export default function ArticleCard({ title, excerpt }: { title: string; excerpt: string }) {
  return (
    <article className="w-64 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{excerpt}</p>
    </article>
  );
}
'''}})

case("fv-011", FV,
     "O input de components/EmailField.tsx não dá nenhum feedback visual quando focado. Adiciona focus ring decente.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/EmailField.tsx", "pattern": "focus:ring|focus-visible:ring|focus:border|focus-visible:outline"}],
     setup={"files": {"components/EmailField.tsx": '''export default function EmailField() {
  return (
    <div className="space-y-1.5">
      <label htmlFor="email" className="text-sm font-medium">E-mail</label>
      <input
        id="email"
        type="email"
        placeholder="voce@exemplo.com"
        className="h-10 w-full rounded-xl border border-zinc-300 bg-white px-3 text-sm outline-none dark:border-zinc-700 dark:bg-zinc-900"
      />
    </div>
  );
}
'''}})

case("fv-012", FV,
     "As trocas de cor no hover do components/LinkList.tsx acontecem de forma seca, sem suavidade. Adiciona transições discretas.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/LinkList.tsx", "pattern": "transition"}],
     setup={"files": {"components/LinkList.tsx": '''import Link from "next/link";

const items = [
  { label: "Documentação", href: "/docs" },
  { label: "Guias", href: "/guias" },
  { label: "API", href: "/api" },
];

export default function LinkList() {
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.href}>
          <Link href={item.href} className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
            {item.label}
          </Link>
        </li>
      ))}
    </ul>
  );
}
'''}})

case("fv-013", FV,
     "O components/MixedCard.tsx mistura três raios de canto diferentes e fica visualmente bagunçado. Padroniza seguindo o guia (superfície 2xl, interativos xl).",
     [{"type": "tsc"},
      {"type": "file_not_contains", "path": "components/MixedCard.tsx", "pattern": "rounded-sm|rounded-3xl"}],
     setup={"files": {"components/MixedCard.tsx": '''export default function MixedCard() {
  return (
    <div className="rounded-sm border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="text-base font-semibold tracking-tight">Plano Pro</h3>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Tudo do Básico, mais relatórios avançados.</p>
      <div className="mt-4 flex gap-2">
        <button className="rounded-3xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900">
          Assinar
        </button>
        <button className="rounded border border-zinc-300 px-4 py-2 text-sm transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800">
          Detalhes
        </button>
      </div>
    </div>
  );
}
'''}})

case("fv-014", FV,
     "O components/Footer.tsx cola no conteúdo acima, sem separação nenhuma. Dá respiro e separação visual.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/Footer.tsx", "pattern": "mt-|py-|border-t"}],
     setup={"files": {"components/Footer.tsx": '''export default function Footer() {
  return (
    <footer>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">© 2026 Eidos. Todos os direitos reservados.</p>
    </footer>
  );
}
'''}})

case("fv-015", FV,
     "Os dois botões do components/CtaPair.tsx têm o mesmo peso visual e o usuário não sabe qual é a ação principal. Cria hierarquia (primário + secundário).",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/CtaPair.tsx", "pattern": "border|ghost|secondary"}],
     setup={"files": {"components/CtaPair.tsx": '''export default function CtaPair() {
  return (
    <div className="flex items-center gap-3">
      <button className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700">
        Criar conta
      </button>
      <button className="rounded-xl bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-zinc-700">
        Falar com vendas
      </button>
    </div>
  );
}
'''}})

case("fv-016", FV,
     "O texto do components/About.tsx está justificado e cria rios de espaço horríveis. Corrige o alinhamento.",
     [{"type": "tsc"},
      {"type": "file_not_contains", "path": "components/About.tsx", "pattern": "text-justify"}],
     setup={"files": {"components/About.tsx": '''export default function About() {
  return (
    <section className="mx-auto max-w-2xl py-16">
      <h2 className="text-2xl font-bold tracking-tight">Sobre nós</h2>
      <p className="mt-4 text-justify text-sm leading-6 text-zinc-600 dark:text-zinc-400">
        Somos um time pequeno construindo ferramentas de interface com atenção obsessiva a detalhes.
        Acreditamos que bom design é invisível: quando funciona, ninguém percebe o esforço.
      </p>
    </section>
  );
}
'''}})

case("fv-017", FV,
     "No mobile, o conteúdo do components/PricingSection.tsx encosta nas bordas da tela. Adiciona padding horizontal no container.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/PricingSection.tsx", "pattern": "px-4|px-6|p-4|p-6"}],
     setup={"files": {"components/PricingSection.tsx": '''export default function PricingSection() {
  return (
    <section className="mx-auto max-w-6xl py-16">
      <h2 className="text-center text-2xl font-bold tracking-tight">Planos</h2>
      <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-3">
        {["Básico", "Pro", "Enterprise"].map((plano) => (
          <div key={plano} className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <h3 className="text-base font-semibold tracking-tight">{plano}</h3>
          </div>
        ))}
      </div>
    </section>
  );
}
'''}})

case("fv-018", FV,
     "Os links do components/InlineLinks.tsx não dão nenhuma pista visual de que são clicáveis no hover. Corrige.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/InlineLinks.tsx", "pattern": "hover:underline|hover:text|underline-offset"}],
     setup={"files": {"components/InlineLinks.tsx": '''import Link from "next/link";

export default function InlineLinks() {
  return (
    <p className="text-sm text-zinc-600 dark:text-zinc-400">
      Leia os <Link href="/termos" className="font-medium text-zinc-900 dark:text-zinc-100">termos de uso</Link> e a{" "}
      <Link href="/privacidade" className="font-medium text-zinc-900 dark:text-zinc-100">política de privacidade</Link>.
    </p>
  );
}
'''}})

case("fv-019", FV,
     "O dropdown do components/UserMenu.tsx abre ATRÁS do conteúdo da página. Corrige o empilhamento.",
     [{"type": "tsc"},
      {"type": "file_contains", "path": "components/UserMenu.tsx", "pattern": "z-\\d+|z-50|z-40"}],
     setup={"files": {"components/UserMenu.tsx": '''"use client";

import { useState } from "react";

export default function UserMenu() {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-200 text-sm font-medium transition-colors hover:bg-zinc-300 dark:bg-zinc-800 dark:hover:bg-zinc-700"
        aria-label="Abrir menu do usuário"
      >
        LF
      </button>
      {open ? (
        <div className="absolute right-0 mt-2 w-48 rounded-xl border border-zinc-200 bg-white p-1 shadow-md dark:border-zinc-800 dark:bg-zinc-900">
          <button className="w-full rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800">Perfil</button>
          <button className="w-full rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-800">Sair</button>
        </div>
      ) : null}
    </div>
  );
}
'''}})

case("fv-020", FV,
     "O components/FullBleed.tsx causa scrollbar horizontal na página inteira (uso de w-screen). Corrige sem perder o efeito de largura total.",
     [{"type": "tsc"},
      {"type": "file_not_contains", "path": "components/FullBleed.tsx", "pattern": "w-screen"}],
     setup={"files": {"components/FullBleed.tsx": '''export default function FullBleed() {
  return (
    <section className="w-screen bg-zinc-900 py-16 text-white dark:bg-zinc-100 dark:text-zinc-900">
      <div className="mx-auto max-w-6xl px-4">
        <h2 className="text-2xl font-bold tracking-tight">Faixa de destaque</h2>
        <p className="mt-2 text-sm opacity-80">Conteúdo em largura total com container interno.</p>
      </div>
    </section>
  );
}
'''}})

# ============================================================ create-component (30)
CC = "create-component"


def cc(id, prompt, path, extra_checks=None, client=False):
    checks = [
        {"type": "file_exists", "path": path},
        {"type": "tsc"},
        {"type": "file_contains", "path": path, "pattern": "export default"},
        {"type": "file_contains", "path": path, "pattern": "dark:"},
        {"type": "file_contains", "path": path, "pattern": "rounded-|rounded "},
    ]
    if client:
        checks.append({"type": "file_contains", "path": path, "pattern": '"use client"'})
    checks.extend(extra_checks or [])
    case(id, CC, prompt + " Siga o guia de estilo do projeto (dark mode, estados, espaçamento).", checks, max_iters=5)


cc("cc-001",
   "Cria um card de métrica em components/MetricCard.tsx: recebe label, value e delta (variação percentual). Delta positivo em verde, negativo em vermelho.",
   "components/MetricCard.tsx",
   [{"type": "file_contains", "path": "components/MetricCard.tsx", "pattern": "type|interface"},
    {"type": "file_contains", "path": "components/MetricCard.tsx", "pattern": "green|emerald"},
    {"type": "file_contains", "path": "components/MetricCard.tsx", "pattern": "red-|rose-"}])

cc("cc-002",
   "Cria um card de plano de preços em components/PricingCard.tsx: nome do plano, preço mensal, lista de features e botão de CTA. Deve aceitar uma prop highlighted pro plano em destaque.",
   "components/PricingCard.tsx",
   [{"type": "file_contains", "path": "components/PricingCard.tsx", "pattern": "highlighted"},
    {"type": "file_contains", "path": "components/PricingCard.tsx", "pattern": "hover:|focus-visible:"}])

cc("cc-003",
   "Cria um componente de depoimento em components/Testimonial.tsx: citação, nome do autor, cargo, e avatar com as iniciais do autor (sem imagem).",
   "components/Testimonial.tsx",
   [{"type": "file_contains", "path": "components/Testimonial.tsx", "pattern": "blockquote|figure"}])

cc("cc-004",
   "Cria um estado vazio em components/EmptyState.tsx: título, descrição e um botão de ação opcional. É o que aparece quando uma lista não tem itens.",
   "components/EmptyState.tsx",
   [{"type": "file_contains", "path": "components/EmptyState.tsx", "pattern": "type|interface"}])

cc("cc-005",
   "Cria um Badge em components/Badge.tsx com variants: success, warning, error e neutral, cada uma com cor semântica adequada nos dois temas.",
   "components/Badge.tsx",
   [{"type": "file_contains", "path": "components/Badge.tsx", "pattern": "success"},
    {"type": "file_contains", "path": "components/Badge.tsx", "pattern": "warning"},
    {"type": "file_contains", "path": "components/Badge.tsx", "pattern": "error"}])

cc("cc-006",
   "Cria um Avatar em components/Avatar.tsx que mostra as iniciais do nome, com tamanhos sm, md e lg.",
   "components/Avatar.tsx",
   [{"type": "file_contains", "path": "components/Avatar.tsx", "pattern": "sm"},
    {"type": "file_contains", "path": "components/Avatar.tsx", "pattern": "rounded-full"}])

cc("cc-007",
   "Cria components/StatGrid.tsx: uma grade responsiva de estatísticas (label + valor), 1 coluna no mobile e 3 no desktop, recebendo os dados por prop.",
   "components/StatGrid.tsx",
   [{"type": "file_contains", "path": "components/StatGrid.tsx", "pattern": "grid"},
    {"type": "file_contains", "path": "components/StatGrid.tsx", "pattern": "sm:|md:|lg:"}])

cc("cc-008",
   "Cria uma seção hero em components/HeroSection.tsx: headline grande, subtítulo e dois CTAs (primário e secundário), centralizada e responsiva.",
   "components/HeroSection.tsx",
   [{"type": "file_contains", "path": "components/HeroSection.tsx", "pattern": "tracking-tight"},
    {"type": "file_contains", "path": "components/HeroSection.tsx", "pattern": "sm:|lg:"}])

cc("cc-009",
   "Cria components/FeatureCard.tsx: um card de feature com um slot pra ícone (ReactNode), título e descrição.",
   "components/FeatureCard.tsx",
   [{"type": "file_contains", "path": "components/FeatureCard.tsx", "pattern": "ReactNode"}])

cc("cc-010",
   "Cria um Alert em components/Alert.tsx com variants info, success e error, título e mensagem, com cores semânticas nos dois temas.",
   "components/Alert.tsx",
   [{"type": "file_contains", "path": "components/Alert.tsx", "pattern": "info"},
    {"type": "file_contains", "path": "components/Alert.tsx", "pattern": "role=|aria-"}])

cc("cc-011",
   "Cria components/Tabs.tsx: abas controladas por estado (client), recebendo uma lista de {label, content}. A aba ativa tem indicador visual claro.",
   "components/Tabs.tsx",
   [{"type": "file_contains", "path": "components/Tabs.tsx", "pattern": "useState"}],
   client=True)

cc("cc-012",
   "Cria components/FaqItem.tsx: item de FAQ expansível (client) — pergunta clicável que revela a resposta, com indicador de aberto/fechado.",
   "components/FaqItem.tsx",
   [{"type": "file_contains", "path": "components/FaqItem.tsx", "pattern": "useState"},
    {"type": "file_contains", "path": "components/FaqItem.tsx", "pattern": "aria-expanded"}],
   client=True)

cc("cc-013",
   "Cria components/ToggleSwitch.tsx: um switch on/off acessível (client), com label, animação suave do thumb e estado visual claro nos dois temas.",
   "components/ToggleSwitch.tsx",
   [{"type": "file_contains", "path": "components/ToggleSwitch.tsx", "pattern": "useState"},
    {"type": "file_contains", "path": "components/ToggleSwitch.tsx", "pattern": "aria-checked|role=\\\"switch\\\"|type=\\\"checkbox\\\""},
    {"type": "file_contains", "path": "components/ToggleSwitch.tsx", "pattern": "transition"}],
   client=True)

cc("cc-014",
   "Cria components/ProgressBar.tsx: barra de progresso com label e porcentagem, animada na transição de valor.",
   "components/ProgressBar.tsx",
   [{"type": "file_contains", "path": "components/ProgressBar.tsx", "pattern": "transition|duration"},
    {"type": "file_contains", "path": "components/ProgressBar.tsx", "pattern": "aria-|role="}])

cc("cc-015",
   "Cria components/Skeleton.tsx: placeholder de carregamento com variantes de texto e de card, usando animate-pulse.",
   "components/Skeleton.tsx",
   [{"type": "file_contains", "path": "components/Skeleton.tsx", "pattern": "animate-pulse"}])

cc("cc-016",
   "Cria components/Breadcrumbs.tsx: trilha de navegação recebendo itens {label, href}, com separador visual e o item atual sem link.",
   "components/Breadcrumbs.tsx",
   [{"type": "file_contains", "path": "components/Breadcrumbs.tsx", "pattern": "nav|aria-label"}])

cc("cc-017",
   "Cria components/Pagination.tsx (client): paginação com anterior/próxima e números, página atual destacada, recebendo page, totalPages e onPageChange.",
   "components/Pagination.tsx",
   [{"type": "file_contains", "path": "components/Pagination.tsx", "pattern": "onPageChange"},
    {"type": "file_contains", "path": "components/Pagination.tsx", "pattern": "disabled"}],
   client=True)

cc("cc-018",
   "Cria components/SearchInput.tsx: campo de busca com ícone de lupa (pode ser SVG inline), placeholder e focus ring caprichado.",
   "components/SearchInput.tsx",
   [{"type": "file_contains", "path": "components/SearchInput.tsx", "pattern": "svg|Search"},
    {"type": "file_contains", "path": "components/SearchInput.tsx", "pattern": "focus"}])

cc("cc-019",
   "Cria components/Modal.tsx (client): modal com overlay escurecido, painel centralizado, título e botão de fechar acessível. Fecha ao clicar no overlay.",
   "components/Modal.tsx",
   [{"type": "file_contains", "path": "components/Modal.tsx", "pattern": "fixed inset-0|fixed"},
    {"type": "file_contains", "path": "components/Modal.tsx", "pattern": "aria-label|aria-modal"}],
   client=True)

cc("cc-020",
   "Cria components/Tooltip.tsx: tooltip só com CSS (group-hover), sem estado — o texto aparece acima do elemento no hover.",
   "components/Tooltip.tsx",
   [{"type": "file_contains", "path": "components/Tooltip.tsx", "pattern": "group-hover"}])

cc("cc-021",
   "Cria components/Timeline.tsx: linha do tempo vertical com marcador, título, data e descrição por item, recebendo os itens por prop.",
   "components/Timeline.tsx",
   [{"type": "file_contains", "path": "components/Timeline.tsx", "pattern": "type|interface"}])

cc("cc-022",
   "Cria components/TeamMemberCard.tsx: card de membro do time com avatar de iniciais, nome, cargo e links sociais (pode usar placeholders de href).",
   "components/TeamMemberCard.tsx",
   [{"type": "file_contains", "path": "components/TeamMemberCard.tsx", "pattern": "hover:"}])

cc("cc-023",
   "Cria components/NewsletterForm.tsx (client): input de e-mail + botão inscrever; após enviar, troca pra mensagem de sucesso (só estado local, sem backend).",
   "components/NewsletterForm.tsx",
   [{"type": "file_contains", "path": "components/NewsletterForm.tsx", "pattern": "useState"},
    {"type": "file_contains", "path": "components/NewsletterForm.tsx", "pattern": "type=\\\"email\\\""}],
   client=True)

cc("cc-024",
   "Cria components/SiteFooter.tsx: rodapé com 3 colunas de links (produto, empresa, legal), divisor superior e copyright, responsivo.",
   "components/SiteFooter.tsx",
   [{"type": "file_contains", "path": "components/SiteFooter.tsx", "pattern": "footer"},
    {"type": "file_contains", "path": "components/SiteFooter.tsx", "pattern": "grid|flex"}])

cc("cc-025",
   "Cria components/DataTable.tsx: tabela estilizada recebendo columns e rows, com cabeçalho destacado, zebra sutil e hover na linha.",
   "components/DataTable.tsx",
   [{"type": "file_contains", "path": "components/DataTable.tsx", "pattern": "table|thead"},
    {"type": "file_contains", "path": "components/DataTable.tsx", "pattern": "hover:"}])

cc("cc-026",
   "Cria components/ThemeToggle.tsx (client): botão que alterna a classe dark no html, com ícones de sol/lua (SVG inline) e aria-label.",
   "components/ThemeToggle.tsx",
   [{"type": "file_contains", "path": "components/ThemeToggle.tsx", "pattern": "classList|documentElement"},
    {"type": "file_contains", "path": "components/ThemeToggle.tsx", "pattern": "aria-label"}],
   client=True)

cc("cc-027",
   "Cria components/Stepper.tsx: indicador horizontal de etapas (1, 2, 3...) com etapa atual destacada, concluídas marcadas e conectores entre elas.",
   "components/Stepper.tsx",
   [{"type": "file_contains", "path": "components/Stepper.tsx", "pattern": "current|active|step"}])

cc("cc-028",
   "Cria components/NotificationCard.tsx: item de notificação com indicador de não-lida (dot), título, resumo e timestamp relativo (string).",
   "components/NotificationCard.tsx",
   [{"type": "file_contains", "path": "components/NotificationCard.tsx", "pattern": "unread|lida"}])

cc("cc-029",
   "Cria components/UploadDropzone.tsx: área de upload visual (borda tracejada, ícone, instrução, hover state) — só a aparência, sem lógica de upload.",
   "components/UploadDropzone.tsx",
   [{"type": "file_contains", "path": "components/UploadDropzone.tsx", "pattern": "dashed"},
    {"type": "file_contains", "path": "components/UploadDropzone.tsx", "pattern": "hover:"}])

cc("cc-030",
   "Cria components/BannerCta.tsx: faixa de CTA com gradiente sutil de fundo, headline, texto de apoio e botão, responsiva.",
   "components/BannerCta.tsx",
   [{"type": "file_contains", "path": "components/BannerCta.tsx", "pattern": "gradient"}])

# ============================================================ terminal-ops (20)
TO = "terminal-ops"

case("to-001", TO,
     "Instala clsx e tailwind-merge e refatora o cn() de lib/utils.ts pra usar os dois (twMerge(clsx(...))).",
     [{"type": "package_dep", "name": "clsx"},
      {"type": "package_dep", "name": "tailwind-merge"},
      {"type": "file_contains", "path": "lib/utils.ts", "pattern": "twMerge"},
      {"type": "tsc"}])

case("to-002", TO,
     "Instala o lucide-react e troca o texto 'eidos' do logo no Navbar por um ícone Sparkles acompanhado do texto.",
     [{"type": "package_dep", "name": "lucide-react"},
      {"type": "file_contains", "path": "components/Navbar.tsx", "pattern": "lucide-react"},
      {"type": "tsc"}])

case("to-003", TO,
     "Instala o recharts e cria components/RevenueChart.tsx (client) com um LineChart simples de receita mensal usando dados mockados.",
     [{"type": "package_dep", "name": "recharts"},
      {"type": "file_exists", "path": "components/RevenueChart.tsx"},
      {"type": "file_contains", "path": "components/RevenueChart.tsx", "pattern": "LineChart"},
      {"type": "tsc"}])

case("to-004", TO,
     "Instala o framer-motion e cria components/FadeIn.tsx (client): um wrapper que anima os filhos com fade + slide sutil ao montar.",
     [{"type": "package_dep", "name": "framer-motion"},
      {"type": "file_exists", "path": "components/FadeIn.tsx"},
      {"type": "file_contains", "path": "components/FadeIn.tsx", "pattern": "motion"},
      {"type": "tsc"}])

case("to-005", TO,
     "Instala o @headlessui/react e cria components/Dropdown.tsx usando o Menu deles, estilizado no padrão do projeto.",
     [{"type": "package_dep", "name": "@headlessui/react"},
      {"type": "file_exists", "path": "components/Dropdown.tsx"},
      {"type": "file_contains", "path": "components/Dropdown.tsx", "pattern": "Menu"},
      {"type": "tsc"}])

case("to-006", TO,
     "Adiciona um script 'typecheck' no package.json que roda tsc --noEmit, e executa ele pra confirmar que passa.",
     [{"type": "package_script", "name": "typecheck"},
      {"type": "ran_command", "pattern": "typecheck|tsc"}])

case("to-007", TO,
     "Instala o date-fns e cria lib/dates.ts com um helper timeAgo(date) que devolve texto relativo em pt-BR (usando formatDistanceToNow com o locale ptBR).",
     [{"type": "package_dep", "name": "date-fns"},
      {"type": "file_exists", "path": "lib/dates.ts"},
      {"type": "file_contains", "path": "lib/dates.ts", "pattern": "ptBR|pt-BR"},
      {"type": "tsc"}])

case("to-008", TO,
     "Instala o zod e cria lib/schemas.ts com um schema de formulário de contato (nome, email, mensagem) e o tipo inferido exportado.",
     [{"type": "package_dep", "name": "zod"},
      {"type": "file_exists", "path": "lib/schemas.ts"},
      {"type": "file_contains", "path": "lib/schemas.ts", "pattern": "z\\.object|z\\.infer"},
      {"type": "tsc"}])

case("to-009", TO,
     "Roda o typecheck do projeto e me diz se está tudo certo — não muda nada, só verifica e reporta.",
     [{"type": "ran_command", "pattern": "tsc"}],
     max_iters=3)

case("to-010", TO,
     "Instala o prettier como dev dependency e cria um .prettierrc com aspas duplas e ponto e vírgula habilitados.",
     [{"type": "package_dep", "name": "prettier"},
      {"type": "file_exists", "path": ".prettierrc"}])

case("to-011", TO,
     "Instala o plugin @tailwindcss/forms e registra ele no tailwind.config.ts.",
     [{"type": "package_dep", "name": "@tailwindcss/forms"},
      {"type": "file_contains", "path": "tailwind.config.ts", "pattern": "forms"},
      {"type": "tsc"}])

case("to-012", TO,
     "Instala o next-themes e configura o ThemeProvider no app/layout.tsx (com attribute='class'), criando o client component wrapper se precisar.",
     [{"type": "package_dep", "name": "next-themes"},
      {"type": "file_contains", "path": "app/layout.tsx", "pattern": "ThemeProvider|Providers"},
      {"type": "tsc"}])

case("to-013", TO,
     "Cria a pasta components/ui e move o Button.tsx pra ela, atualizando todos os imports que apontavam pro caminho antigo.",
     [{"type": "file_exists", "path": "components/ui/Button.tsx"},
      {"type": "tsc"}])

case("to-014", TO,
     "Instala o react-hook-form e cria components/LoginForm.tsx (client) com campos de e-mail e senha validados (required) e mensagens de erro estilizadas.",
     [{"type": "package_dep", "name": "react-hook-form"},
      {"type": "file_exists", "path": "components/LoginForm.tsx"},
      {"type": "file_contains", "path": "components/LoginForm.tsx", "pattern": "useForm"},
      {"type": "tsc"}])

case("to-015", TO,
     "Roda o build de produção e me reporta o resultado (passou? quanto tempo? algum warning?). Não mude nada.",
     [{"type": "ran_command", "pattern": "next build|npm run build|npx next build"}],
     max_iters=3)

case("to-016", TO,
     "Instala o sonner e adiciona o <Toaster /> no layout, com um exemplo de uso comentado.",
     [{"type": "package_dep", "name": "sonner"},
      {"type": "file_contains", "path": "app/layout.tsx", "pattern": "Toaster"},
      {"type": "tsc"}])

case("to-017", TO,
     "Cria um app/robots.txt permitindo tudo e apontando pro sitemap em /sitemap.xml.",
     [{"type": "file_exists", "path": "app/robots.txt"},
      {"type": "file_contains", "path": "app/robots.txt", "pattern": "User-[Aa]gent"}],
     max_iters=3)

case("to-018", TO,
     "Instala o embla-carousel-react e cria components/Carousel.tsx (client) com um carrossel básico de slides recebidos por prop.",
     [{"type": "package_dep", "name": "embla-carousel-react"},
      {"type": "file_exists", "path": "components/Carousel.tsx"},
      {"type": "file_contains", "path": "components/Carousel.tsx", "pattern": "useEmblaCarousel"},
      {"type": "tsc"}])

case("to-019", TO,
     "Preenche o campo description do package.json com 'Template de avaliação do Conatus Eidos' (pode usar npm pkg set).",
     [{"type": "file_contains", "path": "package.json", "pattern": "Template de avalia"}],
     max_iters=3)

case("to-020", TO,
     "Instala o @radix-ui/react-dialog e cria components/ConfirmDialog.tsx (client): diálogo de confirmação com título, descrição e botões confirmar/cancelar estilizados no padrão do projeto.",
     [{"type": "package_dep", "name": "@radix-ui/react-dialog"},
      {"type": "file_exists", "path": "components/ConfirmDialog.tsx"},
      {"type": "file_contains", "path": "components/ConfirmDialog.tsx", "pattern": "Dialog"},
      {"type": "tsc"}])

# ============================================================ emitir
assert len(cases) == 100, f"esperava 100 casos, tenho {len(cases)}"
by_family = {}
for c in cases:
    by_family.setdefault(c["family"], []).append(c["id"])
ids = [c["id"] for c in cases]
assert len(ids) == len(set(ids)), "ids duplicados"

with open(OUT, "w", encoding="utf-8") as f:
    for c in cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")

print(f"{len(cases)} casos -> {OUT}")
for fam, lst in by_family.items():
    print(f"  {fam}: {len(lst)}")
