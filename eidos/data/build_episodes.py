"""Builder de episódios de treino do Eidos (Fase 1/2).

Cada cenário é código Python (batch_eNNN.py) que descreve: setup (arquivos plantados),
CoTs escritos à mão e a sequência de ações. Este builder EXECUTA cada ação de verdade
com os executores do próprio harness (run_eval.py) e grava o output real no turno tool —
nenhum output de ferramenta é inventado. Invariantes são validadas na construção:

    - todo turno assistant com tool call tem CoT não-vazio antes da tag <tool_call>
    - o resultado real precisa casar com o `expect` do cenário (QA por execução)
    - camadas de código (L1-L5) terminam com verificação verde quando o cenário promete
    - LC não pode ter nenhum turno tool
    - episódio termina com turno assistant SEM tool call (o resumo)

Uso:
    python eidos/data/build_episodes.py batch_e001
    -> emite eidos/data/episodes_e001.jsonl
"""
import argparse
import importlib
import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent
EIDOS = DATA.parent
sys.path.insert(0, str(EIDOS))
sys.path.insert(0, str(DATA))

from run_eval import EXECUTORS, apply_setup, reset_workdir, validate_args  # noqa: E402

WORKDIR = EIDOS / ".work_gen"
TOOL_CALL_FMT = "{cot}\n<tool_call>\n{payload}\n</tool_call>"


class ScenarioError(AssertionError):
    pass


class Episode:
    def __init__(self, layer: str, scenario: str, setup: dict | None = None,
                 lang: str = "pt-BR", batch: str = ""):
        self.layer, self.scenario, self.lang, self.batch = layer, scenario, lang, batch
        self.messages: list[dict] = []
        self.workdir = WORKDIR
        reset_workdir(self.workdir)
        apply_setup(self.workdir, setup or {})

    # ---------------- turnos ----------------

    def user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        return self

    def act(self, cot: str, tool: str, expect: str | None = None, **args) -> str:
        """CoT + tool call + execução REAL + turno tool com o output autêntico."""
        if not cot or not cot.strip():
            raise ScenarioError(f"{self.scenario}: CoT vazio antes de {tool}")
        payload = json.dumps({"name": tool, "arguments": args}, ensure_ascii=False)
        self.messages.append({"role": "assistant",
                              "content": TOOL_CALL_FMT.format(cot=cot.strip(), payload=payload)})
        err = validate_args(tool, args)
        result = err if err else EXECUTORS[tool](self.workdir, args)
        self.messages.append({"role": "tool", "content": result})
        if expect and not re.search(expect, result, re.DOTALL):
            raise ScenarioError(
                f"{self.scenario}: resultado de {tool} não casa com expect={expect!r}\n"
                f"--- resultado real ---\n{result[:1500]}")
        return result

    def verify_green(self, cot: str) -> str:
        """Conveniência: roda o typecheck e EXIGE exit 0 — o fecho do ciclo."""
        return self.act(cot, "run_terminal", expect=r"\[exit 0\]", command="npx tsc --noEmit")

    def final(self, text: str):
        if not text or not text.strip():
            raise ScenarioError(f"{self.scenario}: resumo final vazio")
        if "<tool_call>" in text:
            raise ScenarioError(f"{self.scenario}: resumo final não pode ter tool call")
        self.messages.append({"role": "assistant", "content": text.strip()})
        return self

    # ---------------- validação e emissão ----------------

    def build(self) -> dict:
        if not self.messages or self.messages[0]["role"] != "user":
            raise ScenarioError(f"{self.scenario}: episódio precisa começar com turno user")
        if self.messages[-1]["role"] != "assistant" or "<tool_call>" in self.messages[-1]["content"]:
            raise ScenarioError(f"{self.scenario}: episódio precisa terminar com assistant SEM tool call")
        tool_turns = [m for m in self.messages if m["role"] == "tool"]
        if self.layer == "LC" and tool_turns:
            raise ScenarioError(f"{self.scenario}: LC não pode ter turno tool")
        if self.layer != "LC" and not tool_turns:
            raise ScenarioError(f"{self.scenario}: camada {self.layer} sem nenhuma ação")
        return {"layer": self.layer, "lang": self.lang, "messages": self.messages,
                "_meta": {"scenario": self.scenario, "batch": self.batch}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", help="nome do módulo, ex.: batch_e001")
    args = ap.parse_args()

    module = importlib.import_module(args.batch)
    episodes = []
    for i, fn in enumerate(module.EPISODES):
        ep = fn(lambda layer, scenario, **kw: Episode(layer, scenario, batch=args.batch, **kw))
        episodes.append(ep.build())
        print(f"  [{i + 1}/{len(module.EPISODES)}] {ep.scenario} ({ep.layer}) ok "
              f"({sum(1 for m in ep.messages if m['role'] == 'tool')} ações)")

    from collections import Counter
    dist = Counter(e["layer"] for e in episodes)
    out = DATA / f"episodes_{args.batch.removeprefix('batch_')}.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        for e in episodes:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"\n{len(episodes)} episódios -> {out}")
    print("  por camada:", dict(sorted(dist.items())))


if __name__ == "__main__":
    main()
