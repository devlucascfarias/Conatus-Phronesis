"""Smoke test do harness: roda run_case de ponta a ponta com um agente ROTEIRIZADO
(sem modelo, sem GPU). Prova que loop, executores, checks e métricas funcionam.

Roteiros:
    to-017  cria app/robots.txt via write_file           -> deve dar SUCCESS
    fb-020  lê o utils quebrado, conserta via write_file -> deve dar SUCCESS
    fv-001  edita o PlainButton adicionando estados      -> deve dar SUCCESS
    fb-002  agente teimoso: repete a MESMA edição errada -> deve dar FAIL
            e registrar blind_repeat (testa a métrica de repetição cega)

Uso:  python eidos/smoke_test.py
"""
import json

from run_eval import EIDOS, aggregate, run_case

WORKDIR = EIDOS / ".work"


def scripted(replies):
    """generate() que devolve as respostas na ordem; depois, resposta final sem tool."""
    it = iter(replies)

    def generate(messages):
        try:
            return next(it)
        except StopIteration:
            return "Concluído: tarefa finalizada e verificada."

    return generate


def tool(name, **args):
    return ("Executando.\n<tool_call>\n"
            + json.dumps({"name": name, "arguments": args}, ensure_ascii=False)
            + "\n</tool_call>")


UTILS_FIXED = """export function cn(
  ...classes: Array<string | false | null | undefined>
): string {
  return classes.filter(Boolean).join(" ");
}

export function slugify(text: string): string {
  return text.toLowerCase().replace(/\\s+/g, "-");
}
"""

PLAIN_BUTTON_FIXED = """export default function PlainButton({ children }: { children: React.ReactNode }) {
  return (
    <button className="inline-flex h-10 items-center justify-center rounded-xl bg-zinc-900 px-4 text-sm font-medium text-white transition-colors duration-150 hover:bg-zinc-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-2 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300">
      {children}
    </button>
  );
}
"""

SCRIPTS = {
    "to-017": [
        tool("write_file", path="app/robots.txt",
             content="User-Agent: *\nAllow: /\n\nSitemap: /sitemap.xml\n"),
    ],
    "fb-020": [
        tool("read_file", path="lib/utils.ts"),
        tool("write_file", path="lib/utils.ts", content=UTILS_FIXED),
        tool("run_terminal", command="npx tsc --noEmit"),
    ],
    "fv-001": [
        tool("read_file", path="components/PlainButton.tsx"),
        tool("write_file", path="components/PlainButton.tsx", content=PLAIN_BUTTON_FIXED),
    ],
    # agente teimoso: erra o path, recebe o erro e repete IDÊNTICO duas vezes
    "fb-002": [
        tool("edit_file", path="components/Cardd.tsx", old="lib/utils", new="@/lib/utils"),
        tool("edit_file", path="components/Cardd.tsx", old="lib/utils", new="@/lib/utils"),
        tool("edit_file", path="components/Cardd.tsx", old="lib/utils", new="@/lib/utils"),
    ],
}

EXPECTED = {"to-017": True, "fb-020": True, "fv-001": True, "fb-002": False}


def main():
    cases = {json.loads(l)["id"]: json.loads(l)
             for l in (EIDOS / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    results = []
    failures = []
    for cid, replies in SCRIPTS.items():
        r = run_case(cases[cid], scripted(replies), WORKDIR)
        results.append(r)
        ok = r["success"] == EXPECTED[cid]
        print(f"  {cid}: success={r['success']} (esperado {EXPECTED[cid]}) "
              f"iters={r['iterations']} reacted={r['reacted']} blind={r['blind_repeats']} "
              f"{'OK' if ok else '<<< ERRADO'}")
        if not ok:
            failures.append(cid)
            for c in r["checks"]:
                print(f"      check {c['check']['type']}: {c['passed']}")

    if not any(r["blind_repeats"] > 0 for r in results if r["id"] == "fb-002"):
        failures.append("fb-002(blind_repeats não registrado)")

    print()
    print(json.dumps(aggregate(results), ensure_ascii=False, indent=2))
    if failures:
        print(f"\nSMOKE TEST FALHOU: {failures}")
        raise SystemExit(1)
    print("\nSMOKE TEST OK — harness validado de ponta a ponta")


if __name__ == "__main__":
    main()
