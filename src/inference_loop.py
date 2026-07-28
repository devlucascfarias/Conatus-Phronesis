"""Agente de terminal (Fase 5): gerar → detectar tool_call → executar → devolver.

Uso:
    python src/inference_loop.py --model outputs/merged_8b   # ou id do HF / caminho local

Executores:
    web_search    → Ollama web search (OLLAMA_SEARCH_KEY) → Tavily (TAVILY_API_KEY) → DuckDuckGo, nessa ordem
    python_sandbox → subprocess com timeout 5s, whitelist de imports (math, numpy, sympy), sem rede

Máximo de 3 iterações de tool por turno do usuário.

Também expõe run_agent(...) para uso programático (ex.: célula de demo no Colab), já que o
chat de terminal usa input() e não roda bem dentro de uma célula de notebook.
"""
import argparse
import ast
import difflib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from common import ROOT, extract_tool_calls, load_tools

MAX_TOOL_ITERATIONS = 3
SANDBOX_TIMEOUT_S = 5
ALLOWED_IMPORTS = {"math", "numpy", "sympy", "statistics", "itertools", "fractions", "decimal"}


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def exec_web_search_ollama(query: str) -> str:
    """Ollama web search API. Chave em OLLAMA_SEARCH_KEY (secret do Colab).
    Endpoint documentado: POST https://ollama.com/api/web_search com Bearer token.
    Retorna {"results": [{title, url, content}]} — normalizamos para title/url/snippet."""
    import urllib.request
    key = os.environ["OLLAMA_SEARCH_KEY"]
    req = urllib.request.Request(
        "https://ollama.com/api/web_search",
        data=json.dumps({"query": query}).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    raw = payload.get("results", payload if isinstance(payload, list) else [])
    results = [{"title": r.get("title"), "url": r.get("url"),
                "snippet": (r.get("content") or r.get("snippet") or "")[:300]}
               for r in raw][:5]
    return json.dumps({"results": results}, ensure_ascii=False)


def exec_web_search(query: str) -> str:
    # 1) Ollama web search (preferido: chave já configurada no Colab)
    if os.environ.get("OLLAMA_SEARCH_KEY"):
        try:
            return exec_web_search_ollama(query)
        except Exception as e:
            print(f"[ollama search falhou: {e}; tentando próximo provedor]", file=sys.stderr)
    # 2) Tavily
    if os.environ.get("TAVILY_API_KEY"):
        try:
            from tavily import TavilyClient
            resp = TavilyClient(os.environ["TAVILY_API_KEY"]).search(query, max_results=5)
            results = [{"title": r["title"], "url": r["url"], "snippet": r["content"][:300]}
                       for r in resp.get("results", [])]
            return json.dumps({"results": results}, ensure_ascii=False)
        except Exception as e:
            print(f"[tavily falhou: {e}; tentando DuckDuckGo]", file=sys.stderr)
    # 3) DuckDuckGo (sem chave)
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        results = [{"title": r.get("title"), "url": r.get("href"), "snippet": (r.get("body") or "")[:300]}
                   for r in ddgs.text(query, max_results=5)]
    return json.dumps({"results": results}, ensure_ascii=False)


def check_imports(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return None  # deixa o erro de sintaxe aparecer na execução, é sinal útil pro modelo
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[0]]
        for name in names:
            if name and name not in ALLOWED_IMPORTS:
                return f"ImportError: import de '{name}' não permitido no sandbox (permitidos: {sorted(ALLOWED_IMPORTS)})"
    return None


ALIASES = {"np": "numpy", "sp": "sympy"}


def inject_missing_imports(code: str) -> str:
    """Prepend imports da whitelist que o código usa mas não importa (ex.: math.sin sem
    'import math'). Só cobre módulos permitidos; qualquer outro erro volta cru pro modelo."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code  # deixa o SyntaxError chegar ao modelo, é sinal útil
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.asname or a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported |= {a.asname or a.name for a in node.names}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    lines = []
    for name in sorted(used - imported):
        module = ALIASES.get(name, name)
        if module in ALLOWED_IMPORTS:
            lines.append(f"import {module}\n" if name == module else f"import {module} as {name}\n")
    return "".join(lines) + code


def exec_python_sandbox(code: str) -> str:
    err = check_imports(code)
    if err:
        return err
    code = inject_missing_imports(code)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = f.name
    try:
        proc = subprocess.run([sys.executable, "-I", path], capture_output=True, text=True,
                              timeout=SANDBOX_TIMEOUT_S)
        out = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
        return out.strip() or "(sem saída — use print())"
    except subprocess.TimeoutExpired:
        return f"TimeoutError: execução excedeu {SANDBOX_TIMEOUT_S}s"
    finally:
        Path(path).unlink(missing_ok=True)


EXECUTORS = {"web_search": lambda a: exec_web_search(a["query"]),
             "python_sandbox": lambda a: exec_python_sandbox(a["code"])}

# Assinatura de argumentos → tool. As duas tools do projeto têm parâmetros obrigatórios
# DISJUNTOS ("query" vs "code"), então a chave presente identifica a intenção sem
# ambiguidade — sinal muito mais forte que semelhança de string entre nomes.
_ARG_SIGNATURE = {"code": "python_sandbox", "query": "web_search"}


def repair_tool_name(call: dict) -> tuple[dict, str | None]:
    """Normaliza nome de tool alucinado para o nome real. Devolve (call, nome_original).

    Item 5 do plano de correção (2026-07-26). O 8B treinado inventa nomes de tool com
    frequência — `python_sandro`, `python_sandox`, `python_jupyter_cell`, `python_eval`,
    `python` foram todos observados em data/eval/thinking_8b_eval_notes.md, 4 variações
    distintas só na rodada de sampling. Devolver "tool desconhecida" e deixar o modelo
    tentar de novo NÃO converge: na transcrição real ele responde inventando outro nome
    errado, gastando as 3 iterações do turno sem nunca executar nada.

    O reparo é determinístico e roda antes do dispatch:
      1. nome já válido            → passa direto;
      2. nome inválido, mas os argumentos casam com uma assinatura conhecida → renomeia
         (é o caminho que pega todas as variações observadas, já que todas levavam `code`);
      3. sem assinatura, nome parecido com um válido → renomeia por difflib;
      4. nada disso                → devolve intacto e o erro sobe normalmente.

    Deliberadamente NÃO vive em `common.py`: o validador de dataset precisa REPROVAR
    nome de tool inválido (`check_schema` → `tool_desconhecida:*`), nunca consertar. Só a
    inferência repara; o dado de treino continua estrito.
    """
    name = call.get("name")
    if name in EXECUTORS:
        return call, None
    args = call.get("arguments")
    if isinstance(args, dict):
        for key, target in _ARG_SIGNATURE.items():
            if key in args:
                return {**call, "name": target}, name
    parecidos = difflib.get_close_matches(str(name), list(EXECUTORS), n=1, cutoff=0.6)
    if parecidos:
        return {**call, "name": parecidos[0]}, name
    return call, None


def run_agent(messages, generate, max_iters=MAX_TOOL_ITERATIONS, verbose=True, repairs=None):
    """Loop do agente para UM turno já com a mensagem do usuário em `messages`.
    `generate(messages) -> str` é a função de geração do modelo. Executa tool calls
    (web_search/python_sandbox) e realimenta, até `max_iters` iterações. Retorna a
    lista `messages` atualizada. Usável direto numa célula de notebook (Colab).

    Passe uma lista em `repairs` para coletar os nomes de tool alucinados que foram
    reparados, como tuplas (nome_gerado, nome_real) — é a métrica que diz se o problema
    ainda existe no checkpoint, já que o reparo o torna invisível na saída."""
    if repairs is None:
        repairs = []
    for _ in range(max_iters + 1):
        reply = generate(messages)
        messages.append({"role": "assistant", "content": reply})
        if verbose:
            print(f"modelo> {reply}\n")
        calls = [c for c in extract_tool_calls(reply) if "_invalid" not in c]
        if not calls:
            break
        call, alucinado = repair_tool_name(calls[0])
        if alucinado is not None:
            repairs.append((alucinado, call["name"]))
            if verbose:
                print(f"[nome de tool reparado: '{alucinado}' -> '{call['name']}']\n")
        executor = EXECUTORS.get(call.get("name"))
        if not executor:
            # Só chega aqui se nem a assinatura de argumentos nem a semelhança de nome
            # resolveram — aí o erro precisa ser DIRETIVO, listando os nomes válidos, em
            # vez do genérico "tool desconhecida" que fazia o modelo inventar outro nome.
            result = (f"Erro: tool '{call.get('name')}' não existe. "
                      f"Tools disponíveis: {', '.join(sorted(EXECUTORS))}. "
                      f"Repita a chamada usando exatamente um desses nomes.")
        else:
            try:
                result = executor(call.get("arguments", {}))
            except (KeyError, TypeError) as e:
                # JSON com schema errado (ex.: {"()": "..."} em vez de {"code": "..."}) não
                # pode derrubar a sessão inteira — vira erro que volta pro modelo, mesmo
                # padrão de "tool desconhecida", pra ele ter chance de se corrigir.
                result = f"Erro: argumentos inválidos para '{call.get('name')}' — {e!r}"
        if verbose:
            print(f"[{call.get('name')}] → {result[:400]}{'…' if len(result) > 400 else ''}\n")
        messages.append({"role": "tool", "content": result})
    else:
        if verbose:
            print("[limite de iterações de tool atingido neste turno]\n")
    return messages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=2048)
    args = ap.parse_args()
    load_env()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Carregando {args.model}…")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto", device_map="auto")
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    # Ver comentario em src/eval_harness.py: silencia o aviso max_new_tokens/max_length que o
    # generation_config.json de alguns bases dispara a cada turno (no-op no Granite 4.1).
    model.generation_config.max_length = None
    tools = load_tools()

    def generate(messages) -> str:
        # Sem `enable_thinking`: no Granite o <think> e comportamento treinado, nao um canal do
        # template (ver src/build_dataset.py). O historico vai inteiro, com os <think> dos
        # turnos anteriores — o template do Granite repassa o content verbatim, e o treino foi
        # renderizado do mesmo jeito.
        prompt = tokenizer.apply_chat_template(
            messages, tools=tools, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            # do_sample=True — greedy puro entra em loop de repeticao variando um numero a cada
            # linha, medido em data/eval/thinking_8b_eval_notes.md. Valores herdados do Qwen3
            # (ver nota em eval_harness.py). Sem seed fixa aqui de proposito: isto e uso
            # interativo/demo, nao comparacao de metricas entre rodadas.
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=True,
                                 temperature=0.6, top_k=20, top_p=0.95,
                                 repetition_penalty=1.15, no_repeat_ngram_size=8,
                                 pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    messages = []
    print("Chat pronto. Ctrl+C ou 'sair' para encerrar.\n")
    while True:
        try:
            user = input("você> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not user or user.lower() in ("sair", "exit", "quit"):
            break
        messages.append({"role": "user", "content": user})
        run_agent(messages, generate, verbose=True)


if __name__ == "__main__":
    main()
