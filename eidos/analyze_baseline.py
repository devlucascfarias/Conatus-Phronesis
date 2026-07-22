"""Analisa os transcripts de uma rodada de eval e resume ONDE cada família falha
(qual check específico reprova mais), sem precisar ler transcript por transcript à mão.

Uso:
    python eidos/analyze_baseline.py [--dir eidos/results] [--slow-top 8]
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

EIDOS = Path(__file__).parent


def check_label(check: dict) -> str:
    t = check["type"]
    if t in ("file_contains", "file_not_contains"):
        return f"{t}:{check['path']}:{check['pattern'][:30]}"
    if t == "file_exists":
        return f"{t}:{check['path']}"
    if t in ("package_dep", "package_script"):
        return f"{t}:{check['name']}"
    if t == "ran_command":
        return f"{t}:{check['pattern'][:30]}"
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=EIDOS / "results")
    ap.add_argument("--slow-top", type=int, default=8)
    args = ap.parse_args()

    transcripts = sorted((args.dir / "transcripts").glob("*.json"))
    if not transcripts:
        raise SystemExit(f"nenhum transcript em {args.dir / 'transcripts'}")

    by_family = defaultdict(list)
    for p in transcripts:
        t = json.loads(p.read_text(encoding="utf-8"))
        by_family[t["family"]].append(t)

    print(f"{len(transcripts)} transcripts em {len(by_family)} famílias\n")

    for fam, ts in sorted(by_family.items()):
        n = len(ts)
        zero_iter = [t["id"] for t in ts if t["iterations"] == 0]
        one_iter_fail = [t["id"] for t in ts if t["iterations"] == 1 and not t["success"]]
        multi_iter_fail = [t["id"] for t in ts if t["iterations"] > 1 and not t["success"]]
        fail_counter = Counter()
        for t in ts:
            if t["success"]:
                continue
            for c in t["checks"]:
                if not c["passed"]:
                    fail_counter[check_label(c["check"])] += 1

        print(f"=== {fam} ({n} casos, {sum(t['success'] for t in ts)} sucesso) ===")
        print(f"  0 iterações (passivo, nenhuma tool chamada): {len(zero_iter)} -> {zero_iter}")
        print(f"  1 iteração e falhou (ação única insuficiente): {len(one_iter_fail)} -> {one_iter_fail}")
        print(f"  >1 iteração e falhou (agiu mais, ainda errou): {len(multi_iter_fail)} -> {multi_iter_fail}")
        print("  checks que mais reprovaram:")
        for label, count in fail_counter.most_common(6):
            print(f"    {count:3d}x  {label}")
        print()

    print("=== outliers de tempo (mais lentos) ===")
    all_ts = [t for ts in by_family.values() for t in ts]
    for t in sorted(all_ts, key=lambda t: -t["elapsed_s"])[:args.slow_top]:
        print(f"  {t['id']:10s} {t['elapsed_s']:6.1f}s  iters={t['iterations']}  success={t['success']}")

    print("\n=== repetição cega (blind_repeats > 0) ===")
    blind = [t["id"] for t in all_ts if t.get("blind_repeats", 0) > 0]
    print(f"  {len(blind)} casos -> {blind}")

    print("\n=== formato: quantos casos usaram SÓ o bloco ```json``` (nunca <tool_call>) ===")
    fenced_only = [t["id"] for t in all_ts if t.get("total_calls", 0) > 0
                   and t.get("fenced_calls", 0) == t.get("total_calls", 0)]
    print(f"  {len(fenced_only)}/{len([t for t in all_ts if t.get('total_calls', 0) > 0])} casos com pelo menos 1 tool call")


if __name__ == "__main__":
    main()
