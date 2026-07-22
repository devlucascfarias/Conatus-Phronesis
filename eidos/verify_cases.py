"""QA dos casos de eval: confere que cada setup plantado se comporta como o caso promete.

    fix-build com check tsc    -> tsc DEVE FALHAR após o setup (senão o caso é vazio)
    fix-build com check build  -> tsc deve PASSAR e build DEVE FALHAR (o bug é Next-specific)
    fix-visual                 -> tsc deve PASSAR (o bug é estético, não de compilação)
    create-component / terminal-ops -> sem setup; nada a verificar aqui

Uso:  python eidos/verify_cases.py [--skip-build]
"""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

from run_eval import EIDOS, apply_setup, reset_workdir

WORKDIR = EIDOS / ".work_verify"


def tsc_ok(cwd: Path) -> bool:
    (cwd / "tsconfig.tsbuildinfo").unlink(missing_ok=True)
    return subprocess.run("npx tsc --noEmit", shell=True, cwd=cwd,
                          capture_output=True, text=True, timeout=300).returncode == 0


def build_ok(cwd: Path) -> bool:
    shutil.rmtree(cwd / ".next", ignore_errors=True)
    return subprocess.run("npm run build", shell=True, cwd=cwd,
                          capture_output=True, text=True, timeout=900).returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true")
    args = ap.parse_args()

    cases = [json.loads(l) for l in (EIDOS / "eval_cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    problems = []

    reset_workdir(WORKDIR)
    assert tsc_ok(WORKDIR), "template limpo NÃO passa no tsc — conserte o template antes"
    print("template limpo: tsc OK")

    for case in cases:
        setup = case.get("setup") or {}
        if not setup.get("files") and not setup.get("delete"):
            continue
        reset_workdir(WORKDIR)
        apply_setup(WORKDIR, setup)
        check_types = {c["type"] for c in case["checks"]}
        fam = case["family"]

        if fam == "fix-build" and "build" in check_types:
            t = tsc_ok(WORKDIR)
            if not t:
                problems.append(f"{case['id']}: esperava tsc PASSAR (bug é Next-specific), mas tsc falha — troque o check para tsc")
                print(f"  {case['id']}: AJUSTAR (tsc já pega o bug)")
                continue
            if args.skip_build:
                print(f"  {case['id']}: tsc passa (build não verificado, --skip-build)")
                continue
            b = build_ok(WORKDIR)
            status = "ok (build falha como esperado)" if not b else "PROBLEMA: build passa com o bug plantado!"
            if b:
                problems.append(f"{case['id']}: build passa com o bug plantado")
            print(f"  {case['id']}: {status}")
        elif fam == "fix-build":
            t = tsc_ok(WORKDIR)
            if t:
                problems.append(f"{case['id']}: tsc passa com o bug plantado — caso vazio")
            print(f"  {case['id']}: {'ok (tsc falha como esperado)' if not t else 'PROBLEMA: tsc passa!'}")
        elif fam == "fix-visual":
            t = tsc_ok(WORKDIR)
            if not t:
                problems.append(f"{case['id']}: setup visual NÃO compila — o bug deveria ser só estético")
            print(f"  {case['id']}: {'ok (compila, bug é estético)' if t else 'PROBLEMA: não compila!'}")

    print()
    if problems:
        print(f"{len(problems)} problema(s):")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)
    print("todos os setups se comportam como prometido")


if __name__ == "__main__":
    main()
