"""Filtros programáticos + dedup (Fase 2, item 2).

Uso:
    python src/validate_data.py data/raw/pilot.jsonl [outros.jsonl ...]

Saídas:
    data/clean/dataset.jsonl        exemplos aprovados
    data/clean/rejected.jsonl       rejeitados, com o motivo
    data/clean/report.json          contagem de rejeição por motivo + distribuição por camada
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from common import ROOT, extract_tool_calls, load_tools, load_yaml, preamble_text, read_jsonl, word_count, TOOL_CALL_RE

CLEAN_DIR = ROOT / "data" / "clean"

# marcadores de "rationale" que não podem aparecer em resposta de camada 0 (deve ser seca)
LAYER0_MARKERS = ["vou buscar", "deixa eu", "não preciso de", "sem precisar de busca", "let me check", "i'll search", "no need to search"]


def tool_schemas() -> dict:
    return {t["function"]["name"]: t["function"]["parameters"] for t in load_tools()}


def check_schema(call: dict, schemas: dict) -> str | None:
    if "_invalid" in call:
        return "tool_call_json_invalido"
    name, args = call.get("name"), call.get("arguments")
    if name not in schemas:
        return f"tool_desconhecida:{name}"
    if not isinstance(args, dict):
        return "arguments_nao_objeto"
    schema = schemas[name]
    for req in schema.get("required", []):
        if req not in args:
            return f"argumento_obrigatorio_ausente:{req}"
    props = schema.get("properties", {})
    for key, val in args.items():
        if key not in props:
            return f"argumento_extra:{key}"
        if props[key].get("type") == "string" and not isinstance(val, str):
            return f"argumento_tipo_errado:{key}"
    return None


def assistant_turns(ex: dict) -> list[str]:
    return [m.get("content") or "" for m in ex["messages"] if m.get("role") == "assistant"]


def shingles(text: str, n: int = 3) -> set:
    words = re.findall(r"\w+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def run_sandbox_code(code: str, timeout: int) -> tuple[str, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        proc = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
        return proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    finally:
        Path(path).unlink(missing_ok=True)


NUM_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def numbers_of(text: str) -> list[str]:
    return [n.replace(",", ".") for n in NUM_RE.findall(text)]


def check_layer2_execution(ex: dict, timeout: int) -> str | None:
    """Executa de verdade cada python_sandbox e confere que o turno tool seguinte bate."""
    msgs = ex["messages"]
    for i, m in enumerate(msgs):
        if m.get("role") != "assistant":
            continue
        for call in extract_tool_calls(m.get("content") or ""):
            if call.get("name") != "python_sandbox":
                continue
            expected = ""
            for m2 in msgs[i + 1:]:
                if m2.get("role") == "tool":
                    expected = m2.get("content") or ""
                    break
            stdout, stderr = run_sandbox_code(call["arguments"].get("code", ""), timeout)
            if "error" in expected.lower() or "traceback" in expected.lower():
                if not stderr:  # o exemplo afirma erro, mas o código roda limpo
                    return "tool_response_afirma_erro_mas_codigo_roda"
                continue
            if stderr and not stdout:
                return "codigo_sandbox_nao_executa"
            exp_nums, got_nums = numbers_of(expected), numbers_of(stdout)
            if exp_nums and not all(any(abs(float(e) - float(g)) < 1e-6 * max(1, abs(float(e))) for g in got_nums) for e in exp_nums[:5]):
                return "resultado_sandbox_nao_bate"
    return None


def validate(files: list[Path]) -> None:
    cfg = load_yaml("configs/gen_config.yaml")
    vcfg = cfg["validation"]
    layers = cfg["layers"]
    schemas = tool_schemas()
    banned = [re.compile(rf"\b{re.escape(s)}\b", re.IGNORECASE) for s in vcfg["banned_slang"]]

    examples = []
    for f in files:
        examples.extend(read_jsonl(f))
    print(f"{len(examples)} exemplos carregados de {len(files)} arquivo(s)")

    kept, rejected = [], []

    def reject(ex, reason):
        rejected.append({"reason": reason, "example": ex})

    # ---- passe 1: filtros por exemplo ----
    stage1 = []
    for ex in examples:
        layer = str(ex.get("layer", ex.get("_task", {}).get("layer", "")))
        turns = assistant_turns(ex)
        if not turns:
            reject(ex, "sem_turno_assistant"); continue
        full_text = "\n".join(turns)

        if "<think>" in full_text:
            reject(ex, "bloco_think_proibido"); continue

        err = next((e for t in turns for c in extract_tool_calls(t) if (e := check_schema(c, schemas))), None)
        if err:
            reject(ex, err); continue

        if next((s.pattern for s in banned if s.search(full_text)), None):
            reject(ex, "giria_proibida"); continue

        limit = layers.get(layer, {}).get("preamble_max_words")
        if layer == "0":
            if TOOL_CALL_RE.search(full_text):
                reject(ex, "camada0_com_tool_call"); continue
            if any(mk in full_text.lower() for mk in LAYER0_MARKERS):
                reject(ex, "camada0_com_preambulo"); continue
        elif limit:
            # Camada 1: o rationale vive no turno com tool_call. Camada 0.5: não há tool_call, e em
            # multi-turno os turnos-ponte iniciais são conversa — o rationale borderline está no
            # ÚLTIMO turno do assistant, o único ao qual o limite se aplica.
            if layer == "0.5":
                to_check = turns[-1:] if turns else []
            else:
                to_check = [t for t in turns if TOOL_CALL_RE.search(t)]
            over = next((t for t in to_check if word_count(preamble_text(t)) > limit), None)
            if over is not None:
                reject(ex, f"preambulo_acima_de_{limit}_palavras"); continue

        if layer == "2":
            err = check_layer2_execution(ex, vcfg["sandbox_exec_timeout_s"])
            if err:
                reject(ex, err); continue

        stage1.append(ex)

    # ---- passe 2: frase-fôrma (6-gramas de rationale com freq > N no corpus) ----
    # Alvo do plano: os RATIONALES (camadas 0.5 e 1), onde variar o fraseado é exigência.
    # Não se aplica à derivação matemática das camadas 2/3, onde repetir a fórmula-padrão
    # (ex.: FV = PMT·((1+i)ⁿ−1)/i) é correto e desejável — consistência, não frase-fôrma.
    n = vcfg["ngram_n"]
    rationale_layers = {"0.5", "1"}
    grams_per_ex = []
    counter = Counter()
    for ex in stage1:
        grams = set()
        ex_layer = str(ex.get("layer", ex.get("_task", {}).get("layer", "")))
        if ex_layer in rationale_layers:
            for t in assistant_turns(ex):
                words = re.findall(r"\w+", preamble_text(t).lower())
                grams |= {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}
        grams_per_ex.append(grams)
        counter.update(grams)
    overused = {g for g, c in counter.items() if c > vcfg["ngram_max_freq"]}
    stage2 = []
    seen_uses = Counter()
    for ex, grams in zip(stage1, grams_per_ex):
        hot = grams & overused
        if hot and any(seen_uses[g] >= vcfg["ngram_max_freq"] for g in hot):
            reject(ex, "frase_forma_repetida"); continue
        seen_uses.update(hot)
        stage2.append(ex)

    # ---- passe 3: dedup por similaridade (Jaccard de 3-gramas) ----
    final, kept_shingles = [], []
    for ex in stage2:
        sh = shingles(json.dumps([m.get("content", "") for m in ex["messages"]], ensure_ascii=False))
        if any(jaccard(sh, other) >= vcfg["dedup_jaccard_threshold"] for other in kept_shingles):
            reject(ex, "duplicado"); continue
        kept_shingles.append(sh)
        final.append(ex)
    kept = final

    # ---- relatório ----
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    with open(CLEAN_DIR / "dataset.jsonl", "w", encoding="utf-8") as f:
        for ex in kept:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    with open(CLEAN_DIR / "rejected.jsonl", "w", encoding="utf-8") as f:
        for r in rejected:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dist = Counter(str(ex.get("layer", ex.get("_task", {}).get("layer", "?"))) for ex in kept)
    report = {
        "input": len(examples),
        "kept": len(kept),
        "rejected_total": len(rejected),
        "rejected_by_reason": dict(Counter(r["reason"] for r in rejected).most_common()),
        "layer_distribution": {k: {"n": v, "share": round(v / max(1, len(kept)), 3)} for k, v in sorted(dist.items())},
        "layer_targets": {k: layers[k]["share"] for k in layers},
    }
    with open(CLEAN_DIR / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Aprovados: {len(kept)} → {CLEAN_DIR / 'dataset.jsonl'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    validate(ap.parse_args().files)
