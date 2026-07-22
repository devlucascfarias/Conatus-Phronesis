import Link from "next/link";
import Button from "@/components/Button";

const links = [
  { label: "Início", href: "/" },
  { label: "Recursos", href: "#recursos" },
  { label: "Preços", href: "#precos" },
];

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          eidos
        </Link>
        <ul className="hidden items-center gap-6 sm:flex">
          {links.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="text-sm text-zinc-600 transition-colors hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
        <Button size="sm">Começar</Button>
      </nav>
    </header>
  );
}
