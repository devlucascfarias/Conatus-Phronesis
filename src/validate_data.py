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

from common import (
    ROOT,
    THINK_TAG_RE,
    TOOL_CALL_RE,
    extract_tool_calls,
    load_tools,
    load_yaml,
    preamble_text,
    read_jsonl,
    strip_think_blocks,
    think_format_error,
    think_text,
    word_count,
)

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

# Traceback de verdade, nao a palavra "error" solta: `alternating_error_bound=0.0099` num
# stdout legitimo casava com um `"error" in texto` ingenuo e reprovava o item (visto no
# task 1338). Exige "Traceback" ou um nome de excecao Python no inicio de linha.
TRACEBACK_RE = re.compile(
    r"^\s*Traceback \(most recent call last\)|^\s*[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Interrupt)\s*:",
    re.MULTILINE,
)


def looks_like_traceback(text: str) -> bool:
    return bool(TRACEBACK_RE.search(text or ""))


def numbers_of(text: str) -> list[str]:
    return [n.replace(",", ".") for n in NUM_RE.findall(text)]


# Números na resposta VISÍVEL do assistant. O corpus é bilíngue: pt-BR usa "." de
# milhar e "," decimal ("6.907,50"); en-US usa o inverso ("$554,395", "0.042212253").
# A mesma grafia "47.426" é ambígua entre locales, então extraímos TODAS as leituras
# plausíveis de cada token — o check só reprova se NENHUMA bate (ambiguidade ⇒ leniência).
ANS_NUM_RE = re.compile(r"-?\d[\d.,]*\d|-?\d")


def _interpretations(tok: str) -> list[float]:
    tok = tok.replace("−", "-")           # minus unicode → hífen ASCII
    out = set()

    def add(s):
        try:
            out.add(float(s))
        except ValueError:
            pass

    add(tok.replace(",", "").replace(" ", ""))            # en-US: "," = milhar
    add(tok.replace(".", "").replace(",", "."))           # pt-BR: "." = milhar, "," = decimal
    if tok.count(",") == 0 and tok.count(".") <= 1:
        add(tok)                                           # decimal simples "6907.5"
    return list(out)


def answer_numbers(text: str) -> list[float]:
    vals = []
    for tok in ANS_NUM_RE.findall((text or "").replace("−", "-")):
        vals.extend(_interpretations(tok))
    return vals


def _answer_after_tool(msgs: list[dict], tool_i: int) -> str | None:
    """Primeira resposta visível do assistant depois do turno tool (sem <think>).

    Tem de ser a que RESPONDE àquele tool, não o último turno da conversa — em
    multi-turno o último assistant costuma responder a outra pergunta.
    """
    for m in msgs[tool_i + 1:]:
        if m.get("role") == "assistant":
            return strip_think_blocks(m.get("content") or "").strip()
    return None


def _echoes(target: float, ans_nums: list[float]) -> bool:
    """A resposta ecoa o resultado se contém o número — inclusive arredondado.

    Para cada número da resposta, confere se o alvo, arredondado à mesma quantidade
    de casas, bate. Assim 26,83 casa com 26.8328 (round legítimo), mas 6.906,75 NÃO
    casa com 6907.5 (corrupção real). floor/int também vale.
    """
    for a in ans_nums:
        s = repr(a)
        d = len(s.split(".")[1]) if "." in s and not s.endswith(".0") else 0
        if abs(round(target, d) - a) < 1e-9:
            return True
        if abs(int(target) - a) < 1e-9:   # truncamento explícito
            return True
    return False


def check_answer_echoes_tool(ex: dict) -> str | None:
    """O resultado do último python_sandbox tem de reaparecer na resposta.

    Fecha o ponto cego de check_sandbox_execution: aquele confere código→turno-tool,
    este confere turno-tool→resposta. Pega o modo de falha do modelo (sandbox devolve
    6907.5 e a resposta escreve 6.906,75).

    Só age quando o stdout tem UM número — headline inequívoca. Stdout com vários
    valores é ambíguo demais pra cobrar mecanicamente; fica pro LLM-juiz.
    """
    msgs = ex["messages"]
    last_tool_i, last_result = None, None
    for i, m in enumerate(msgs):
        if m.get("role") != "assistant":
            continue
        if any(c.get("name") == "python_sandbox" for c in extract_tool_calls(m.get("content") or "")):
            for j in range(i + 1, len(msgs)):
                if msgs[j].get("role") == "tool":
                    last_tool_i, last_result = j, msgs[j].get("content") or ""
                    break
    if last_tool_i is None:
        return None
    tool_nums = numbers_of(last_result)
    if len(tool_nums) != 1:
        return None
    answer = _answer_after_tool(msgs, last_tool_i)
    if not answer:
        return None
    if not _echoes(float(tool_nums[0]), answer_numbers(answer)):
        return "resposta_nao_ecoa_resultado_tool"
    return None


# Só números com separador decimal explícito ("5,0801", "30.6", "0,33%") — inteiros
# soltos ("10 vezes", anos, contagens) são derivados/paráfrase demais pra cobrar
# mecanicamente e geram falso-positivo. É exatamente a precisão falsa observada no bug
# real (compra R$ 5,0801 / venda R$ 5,0907, citado sem existir em nenhum snippet).
WS_PRECISE_NUM_RE = re.compile(r"-?\d[\d.,]*[.,]\d+")


def _websearch_result_text(tool_content: str) -> str:
    """Concatena title+url+snippet de todo resultado do turno tool de web_search."""
    try:
        data = json.loads(tool_content)
    except json.JSONDecodeError:
        return tool_content
    parts = []
    for r in data.get("results", []) if isinstance(data, dict) else []:
        parts += [str(r.get("title", "")), str(r.get("url", "")), str(r.get("snippet", ""))]
    return " ".join(parts) if parts else tool_content


def _final_visible_answer(msgs: list[dict]) -> str | None:
    """Texto da ÚLTIMA mensagem assistant da conversa, sem <think> nem <tool_call> soltos.

    Diferente de _answer_after_tool (que pega o PRIMEIRO assistant depois de um tool
    específico — certo quando esse tool é a última ação da conversa, errado quando vem
    mais tool depois, ex.: web_search seguido de python_sandbox). O grounding de busca
    tem de julgar a resposta final de verdade, não um turno intermediário que ainda tem
    outra tool_call — código de sandbox tem números literais (ex. "1.0115" para 1,15%)
    que não são "citação da busca" e derrubariam o check por engano.
    """
    for m in reversed(msgs):
        if m.get("role") == "assistant":
            visible = strip_think_blocks(m.get("content") or "")
            return TOOL_CALL_RE.sub("", visible).strip()
    return None


def check_websearch_grounding(ex: dict) -> str | None:
    """Todo número com precisão decimal citado na resposta final pós-web_search precisa
    aparecer (em alguma leitura pt-BR/en-US, sinal incluído ou não) nos resultados
    retornados pela busca.

    Fecha o bug real observado: cotação fabricada com 4 casas decimais ("R$ 5,0801")
    atribuída a uma fonte que não estava nos resultados. Só olha o ÚLTIMO web_search
    da conversa — turnos anteriores podem ter sido substituídos por uma busca melhor.

    Só age quando a conversa usa SÓ web_search (nenhum python_sandbox). Quando as duas
    tools aparecem juntas (ex.: busca a taxa, depois calcula payback/juros no sandbox),
    o número final é ARITMÉTICA DERIVADA, não citação — grounded em cálculo, não em
    busca. Cobrar isso aqui duplicaria (mal) o que check_answer_echoes_tool já verifica
    contra o stdout real; misturar os dois conceitos gera falso-positivo mecânico.
    """
    msgs = ex["messages"]
    last_result, has_sandbox = None, False
    for i, m in enumerate(msgs):
        if m.get("role") != "assistant":
            continue
        calls = extract_tool_calls(m.get("content") or "")
        if any(c.get("name") == "python_sandbox" for c in calls):
            has_sandbox = True
        if any(c.get("name") == "web_search" for c in calls):
            for j in range(i + 1, len(msgs)):
                if msgs[j].get("role") == "tool":
                    last_result = msgs[j].get("content") or ""
                    break
    if last_result is None or has_sandbox:
        return None
    answer = _final_visible_answer(msgs)
    if not answer:
        return None
    ans_precise = WS_PRECISE_NUM_RE.findall(answer)
    if not ans_precise:
        return None
    source_text = _websearch_result_text(last_result)
    source_nums = answer_numbers(source_text)
    source_abs = {abs(s) for s in source_nums}
    for tok in ans_precise:
        vals = _interpretations(tok)
        # Sinal pode legitimamente virar: "-2,3%" na busca vira "queda de 2,3%" na
        # fala — compara também por magnitude, não só valor com sinal.
        if not any(_echoes(v, source_nums) or any(abs(abs(v) - a) <= 1e-6 * max(1.0, a) for a in source_abs) for v in vals):
            return "resposta_numero_nao_grounded_em_busca"
    return None


def check_sandbox_execution(ex: dict, timeout: int) -> str | None:
    """Executa de verdade cada python_sandbox e confere que o turno tool seguinte bate.

    Vale para camadas 2 e 3: a camada 3 passou a ter sandbox de verdade (batch_023 em
    diante) e ficava sem reexecucao, um ponto cego real — stdout fabricado passaria batido.
    """
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
            if looks_like_traceback(expected):
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

        if layer in {"0", "0.5", "1", "2", "C"}:
            missing_think = next((t for t in turns if not THINK_TAG_RE.search(t)), None)
            if missing_think is not None:
                reject(ex, "turno_assistant_sem_think"); continue
        turns_with_think = [t for t in turns if THINK_TAG_RE.search(t)]
        think_err = next((err for t in turns_with_think if (err := think_format_error(t))), None)
        if think_err:
            reject(ex, think_err); continue
        think_limit = layers.get(layer, {}).get("think_max_words")
        if think_limit is not None:
            over_think = next((t for t in turns_with_think if word_count(think_text(t)) > think_limit), None)
            if over_think is not None:
                reject(ex, f"think_acima_de_{think_limit}_palavras"); continue

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

        if layer in {"2", "3"}:
            err = check_sandbox_execution(ex, vcfg["sandbox_exec_timeout_s"])
            if err:
                reject(ex, err); continue
            err = check_answer_echoes_tool(ex)
            if err:
                reject(ex, err); continue

        # Não fica preso a camada 2/3: web_search aparece nas camadas 1 e 3 (e a função
        # já é auto-guardada — no-op se não há web_search, ou se há sandbox junto).
        err = check_websearch_grounding(ex)
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
