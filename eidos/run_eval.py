"""Harness de avaliação do Conatus Eidos (Fase 0/4).

Uso (Colab/local, com GPU):
    python eidos/run_eval.py --model Qwen/Qwen2.5-Coder-7B-Instruct [--adapter caminho] \
        [--cases eidos/eval_cases.jsonl] [--only fb-001,fv-002] [--family fix-build] \
        [--out eidos/results]

Também expõe run_case(case, generate, workdir) para uso programático em notebook.

Fluxo por caso:
    1. reset do workdir (copia template_app por cima, remove arquivos extras; node_modules preservado)
    2. aplica setup (files/delete)
    3. loop do agente: generate -> tool call -> executor -> realimenta (até max_iters)
    4. roda os checks; salva transcript em <out>/transcripts/<id>.json

Métricas agregadas:
    success rate por família e total, iterações médias até sucesso, tool_json_valid_rate,
    blind_repeat_rate (repetiu ação idêntica logo após um resultado de erro),
    reacted_to_error_rate (após erro, a ação seguinte foi diferente).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

EIDOS = Path(__file__).parent
sys.path.insert(0, str(EIDOS.parent / "src"))
from common import extract_tool_calls  # noqa: E402

TEMPLATE = EIDOS / "template_app"
MAX_TOOL_RESULT_CHARS = 4000
TERMINAL_TIMEOUT_S = 420
ALLOWED_CMDS = ("npm", "npx", "node", "ls", "cat", "mkdir", "mv", "cp", "touch", "echo")

SYSTEM_PROMPT = """Você é um agente de desenvolvimento frontend trabalhando num projeto Next.js 14 + \
TypeScript + Tailwind. Você tem as ferramentas read_file, write_file, edit_file e run_terminal. \
Trabalhe em passos pequenos: leia antes de editar, rode typecheck/build depois de mudar, leia o \
stderr inteiro antes de reagir a um erro. Responda em português. Quando a tarefa estiver concluída \
e verificada, responda sem chamar ferramenta, resumindo o que fez."""


# ---------------------------------------------------------------- workdir

def list_template_files():
    for p in TEMPLATE.rglob("*"):
        if p.is_file() and "node_modules" not in p.parts and ".next" not in p.parts:
            yield p.relative_to(TEMPLATE)


def reset_workdir(workdir: Path):
    workdir.mkdir(parents=True, exist_ok=True)
    template_set = set(list_template_files())
    for rel in template_set:
        dst = workdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / rel, dst)
    # remove o que não pertence ao template (criações de casos anteriores)
    for p in list(workdir.rglob("*")):
        if not p.is_file():
            continue
        if "node_modules" in p.parts or ".next" in p.parts:
            continue
        if p.name == "tsconfig.tsbuildinfo":
            p.unlink()
            continue
        if p.relative_to(workdir) not in template_set:
            p.unlink()
    next_dir = workdir / ".next"
    if next_dir.exists():
        shutil.rmtree(next_dir, ignore_errors=True)
    if not (workdir / "node_modules").exists():
        print("[setup] instalando node_modules no workdir (uma vez)...")
        subprocess.run("npm install --no-audit --no-fund", shell=True, cwd=workdir,
                       capture_output=True, text=True, timeout=900)


def apply_setup(workdir: Path, setup: dict):
    for rel, content in (setup.get("files") or {}).items():
        dst = workdir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
    for rel in setup.get("delete") or []:
        (workdir / rel).unlink(missing_ok=True)


# ---------------------------------------------------------------- executores

def _safe_path(workdir: Path, rel: str) -> Path | None:
    p = (workdir / rel).resolve()
    return p if str(p).startswith(str(workdir.resolve())) else None


def exec_read_file(workdir: Path, args: dict) -> str:
    p = _safe_path(workdir, args.get("path", ""))
    if p is None or not p.is_file():
        return f"Erro: arquivo não encontrado: {args.get('path')}"
    lines = p.read_text(encoding="utf-8").splitlines()
    return "\n".join(f"{i + 1}\t{l}" for i, l in enumerate(lines)) or "(arquivo vazio)"


def exec_write_file(workdir: Path, args: dict) -> str:
    p = _safe_path(workdir, args.get("path", ""))
    if p is None:
        return "Erro: caminho fora do projeto"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(args.get("content", ""), encoding="utf-8")
    return f"ok: {args.get('path')} gravado ({len(args.get('content', ''))} chars)"


def exec_edit_file(workdir: Path, args: dict) -> str:
    p = _safe_path(workdir, args.get("path", ""))
    if p is None or not p.is_file():
        return f"Erro: arquivo não encontrado: {args.get('path')}"
    text = p.read_text(encoding="utf-8")
    old = args.get("old", "")
    n = text.count(old)
    if n == 0:
        return "Erro: trecho 'old' não encontrado no arquivo (confira espaços e indentação)"
    if n > 1:
        return f"Erro: trecho 'old' aparece {n} vezes; forneça um trecho único"
    p.write_text(text.replace(old, args.get("new", ""), 1), encoding="utf-8")
    return f"ok: {args.get('path')} editado"


def exec_run_terminal(workdir: Path, args: dict) -> str:
    cmd = (args.get("command") or "").strip()
    first = cmd.split(" ", 1)[0] if cmd else ""
    if first not in ALLOWED_CMDS:
        return f"Erro: comando '{first}' não permitido (permitidos: {', '.join(ALLOWED_CMDS)})"
    try:
        proc = subprocess.run(cmd, shell=True, cwd=workdir, capture_output=True,
                              text=True, timeout=TERMINAL_TIMEOUT_S, encoding="utf-8",
                              errors="replace")
    except subprocess.TimeoutExpired:
        return f"TimeoutError: comando excedeu {TERMINAL_TIMEOUT_S}s"
    out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    out = out.strip() or "(sem saída)"
    if len(out) > MAX_TOOL_RESULT_CHARS:
        out = out[:MAX_TOOL_RESULT_CHARS // 2] + "\n[... saída truncada ...]\n" + out[-MAX_TOOL_RESULT_CHARS // 2:]
    return f"[exit {proc.returncode}]\n{out}"


EXECUTORS = {
    "read_file": exec_read_file,
    "write_file": exec_write_file,
    "edit_file": exec_edit_file,
    "run_terminal": exec_run_terminal,
}

ERROR_MARKERS = re.compile(r"\[exit [1-9]|Erro:|error TS|Error:|Failed to compile|TimeoutError", re.IGNORECASE)


# ---------------------------------------------------------------- checks

def run_check(workdir: Path, check: dict, ran_commands: list[str]) -> bool:
    t = check["type"]
    if t == "tsc":
        r = subprocess.run("npx tsc --noEmit", shell=True, cwd=workdir,
                           capture_output=True, text=True, timeout=300)
        return r.returncode == 0
    if t == "build":
        shutil.rmtree(workdir / ".next", ignore_errors=True)
        r = subprocess.run("npm run build", shell=True, cwd=workdir,
                           capture_output=True, text=True, timeout=900)
        return r.returncode == 0
    if t == "file_exists":
        return (workdir / check["path"]).is_file()
    if t in ("file_contains", "file_not_contains"):
        p = workdir / check["path"]
        if not p.is_file():
            return t == "file_not_contains"
        found = re.search(check["pattern"], p.read_text(encoding="utf-8")) is not None
        return found if t == "file_contains" else not found
    if t == "package_dep":
        pkg = json.loads((workdir / "package.json").read_text(encoding="utf-8"))
        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        return check["name"] in deps
    if t == "package_script":
        pkg = json.loads((workdir / "package.json").read_text(encoding="utf-8"))
        return check["name"] in pkg.get("scripts", {})
    if t == "ran_command":
        return any(re.search(check["pattern"], c) for c in ran_commands)
    raise ValueError(f"check desconhecido: {t}")


# ---------------------------------------------------------------- loop do agente

def run_case(case: dict, generate, workdir: Path, verbose=False) -> dict:
    reset_workdir(workdir)
    apply_setup(workdir, case.get("setup") or {})

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": case["prompt"]}]
    ran_commands: list[str] = []
    json_flags: list[bool] = []
    actions: list[str] = []           # assinatura de cada ação, p/ detectar repetição cega
    last_result_was_error = False
    blind_repeats = 0
    reacted = 0
    errors_seen = 0
    iters = 0
    t0 = time.time()

    for _ in range(case.get("max_iters", 6) + 1):
        reply = generate(messages)
        messages.append({"role": "assistant", "content": reply})
        if verbose:
            print(f"  modelo> {reply[:200]}...")
        raw_calls = extract_tool_calls(reply)
        json_flags.extend("_invalid" not in c for c in raw_calls)
        calls = [c for c in raw_calls if "_invalid" not in c]
        if not calls:
            break
        iters += 1
        call = calls[0]
        sig = json.dumps(call, sort_keys=True, ensure_ascii=False)
        if last_result_was_error and errors_seen:
            if actions and sig == actions[-1]:
                blind_repeats += 1
            else:
                reacted += 1
        actions.append(sig)
        executor = EXECUTORS.get(call.get("name"))
        if executor is None:
            result = f"Erro: tool desconhecida '{call.get('name')}'"
        else:
            result = executor(workdir, call.get("arguments") or {})
        if call.get("name") == "run_terminal":
            ran_commands.append((call.get("arguments") or {}).get("command", ""))
        last_result_was_error = ERROR_MARKERS.search(result) is not None
        if last_result_was_error:
            errors_seen += 1
        messages.append({"role": "tool", "content": result})
        if verbose:
            print(f"  [{call.get('name')}] -> {result[:200]}")

    checks = [{"check": c, "passed": run_check(workdir, c, ran_commands)}
              for c in case["checks"]]
    return {
        "id": case["id"], "family": case["family"],
        "success": all(c["passed"] for c in checks),
        "checks": checks, "iterations": iters,
        "errors_seen": errors_seen, "reacted": reacted, "blind_repeats": blind_repeats,
        "json_flags": json_flags, "elapsed_s": round(time.time() - t0, 1),
        "messages": messages, "ran_commands": ran_commands,
    }


# ---------------------------------------------------------------- agregação

def aggregate(results: list[dict]) -> dict:
    fams = defaultdict(list)
    for r in results:
        fams[r["family"]].append(r)
    all_json = [f for r in results for f in r["json_flags"]]
    err_events = sum(r["reacted"] + r["blind_repeats"] for r in results)
    return {
        "n_cases": len(results),
        "success_rate": round(sum(r["success"] for r in results) / max(1, len(results)), 3),
        "per_family": {
            fam: {
                "n": len(rs),
                "success_rate": round(sum(r["success"] for r in rs) / len(rs), 3),
                "avg_iterations": round(sum(r["iterations"] for r in rs) / len(rs), 2),
            } for fam, rs in sorted(fams.items())
        },
        "tool_json_valid_rate": round(sum(all_json) / max(1, len(all_json)), 3) if all_json else None,
        "reacted_to_error_rate": round(
            sum(r["reacted"] for r in results) / err_events, 3) if err_events else None,
        "blind_repeat_rate": round(
            sum(r["blind_repeats"] for r in results) / err_events, 3) if err_events else None,
        "avg_elapsed_s": round(sum(r["elapsed_s"] for r in results) / max(1, len(results)), 1),
    }


# ---------------------------------------------------------------- main

def make_generate(model_id: str, adapter: str | None, max_new_tokens: int):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto", device_map="auto")
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    tools = json.loads((EIDOS / "tools.json").read_text(encoding="utf-8"))["tools"]

    def generate(messages) -> str:
        prompt = tokenizer.apply_chat_template(messages, tools=tools, tokenize=False,
                                               add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                                 no_repeat_ngram_size=10, pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    return generate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--cases", type=Path, default=EIDOS / "eval_cases.jsonl")
    ap.add_argument("--only", default=None, help="ids separados por vírgula")
    ap.add_argument("--family", default=None)
    ap.add_argument("--out", type=Path, default=EIDOS / "results")
    ap.add_argument("--workdir", type=Path, default=EIDOS / ".work")
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    args = ap.parse_args()

    cases = [json.loads(l) for l in args.cases.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    if args.family:
        cases = [c for c in cases if c["family"] == args.family]
    print(f"{len(cases)} casos | modelo: {args.model}" + (f" + {args.adapter}" if args.adapter else ""))

    generate = make_generate(args.model, args.adapter, args.max_new_tokens)
    (args.out / "transcripts").mkdir(parents=True, exist_ok=True)

    results = []
    for i, case in enumerate(cases):
        r = run_case(case, generate, args.workdir)
        results.append(r)
        status = "OK " if r["success"] else "FAIL"
        print(f"  [{i + 1}/{len(cases)}] {r['id']} {status} ({r['iterations']} iters, {r['elapsed_s']}s)")
        transcript = {k: v for k, v in r.items()}
        (args.out / "transcripts" / f"{r['id']}.json").write_text(
            json.dumps(transcript, ensure_ascii=False, indent=1), encoding="utf-8")

    metrics = aggregate(results)
    metrics["model"] = args.model
    metrics["adapter"] = args.adapter
    (args.out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
