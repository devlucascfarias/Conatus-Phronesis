"""Agente de terminal (Fase 5): gerar → detectar tool_call → executar → devolver.

Uso:
    python src/inference_loop.py --model outputs/merged_4b   # ou id do HF / caminho local

Executores:
    web_search    → Ollama web search (OLLAMA_SEARCH_KEY) → Tavily (TAVILY_API_KEY) → DuckDuckGo, nessa ordem
    python_sandbox → subprocess com timeout 5s, whitelist de imports (math, numpy, sympy), sem rede

Máximo de 3 iterações de tool por turno do usuário.

Também expõe run_agent(...) para uso programático (ex.: célula de demo no Colab), já que o
chat de terminal usa input() e não roda bem dentro de uma célula de notebook.
"""
import argparse
import ast
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


def exec_python_sandbox(code: str) -> str:
    err = check_imports(code)
    if err:
        return err
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


def run_agent(messages, generate, max_iters=MAX_TOOL_ITERATIONS, verbose=True):
    """Loop do agente para UM turno já com a mensagem do usuário em `messages`.
    `generate(messages) -> str` é a função de geração do modelo. Executa tool calls
    (web_search/python_sandbox) e realimenta, até `max_iters` iterações. Retorna a
    lista `messages` atualizada. Usável direto numa célula de notebook (Colab)."""
    for _ in range(max_iters + 1):
        reply = generate(messages)
        messages.append({"role": "assistant", "content": reply})
        if verbose:
            print(f"modelo> {reply}\n")
        calls = [c for c in extract_tool_calls(reply) if "_invalid" not in c]
        if not calls:
            break
        call = calls[0]
        executor = EXECUTORS.get(call.get("name"))
        result = executor(call.get("arguments", {})) if executor else f"Erro: tool desconhecida '{call.get('name')}'"
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
    ap.add_argument("--max-new-tokens", type=int, default=768)
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
    tools = load_tools()

    def generate(messages) -> str:
        prompt = tokenizer.apply_chat_template(messages, tools=tools, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=True,
                                 temperature=0.7, top_p=0.9, pad_token_id=tokenizer.eos_token_id)
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
