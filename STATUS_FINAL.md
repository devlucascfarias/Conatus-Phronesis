# Status FINAL do projeto — dataset fechado na iteração 5

> Decisão combinada após a iter-4: o batch_015 seria a última rodada de dados,
> aceitando o resultado que viesse. Veio, e o veredito é: **a iter-5 (443 exemplos)
> é a versão final entregue.** Este arquivo substitui o STATUS_ITER3.md como registro
> de encerramento.

## Placar completo (6 rodadas de eval, 120 casos)

| Métrica | Baseline | Iter-1 (336) | Iter-2 (383) | Iter-3 (407) | Iter-4 (433) | **Iter-5 (443)** |
|---|---|---|---|---|---|---|
| accuracy | 0,85 | 0,725 | 0,825 | **0,90** | 0,875 | 0,875 |
| web_search recall | 0,75 | 0,35 | 0,525 | 0,75 | 0,725 | 0,725 |
| web_search precision | — | — | — | 1,0 | 0,967 | **1,0** |
| web_search F1 | 0,833 | 0,519 | 0,677 | **0,857** | 0,829 | 0,841 |
| python_sandbox recall | 0,70 | 0,65 | **0,95** | 0,90 | 0,85 | 0,80 |
| none precision | 0,784 | 0,645 | 0,747 | **0,833** | 0,808 | 0,800 |
| FP busca em trivial | 3,3% | 0% | 1,7% | 0% | 1,7% | **0%** |
| JSON de tool call válido | — | 1,0 | 1,0 | 1,0 | 1,0 | 1,0 |

## Por que a iter-5 é a final (e não a iter-3, que tem accuracy maior)

- **Punt eliminado** — o pior modo de falha de UX ("consulte o site oficial") sumiu:
  ws-007 (BBB), ws-009 (Mega-Sena) e ws-028 (Oscar) todos buscam, com rationale honesto
  ("não tenho o resultado em memória. Vou buscar").
- **Conversa coerente** — a regressão de camada C da iter-3 (respostas inventadas e
  incoerentes na demo) foi resolvida pelos batches 014-015; a "curiosidade" da demo agora
  responde como gente (pergunta o assunto de interesse em vez de alucinar).
- **Zero over-search** — precision 1,0 e FP-trivial 0% simultâneos, único caso em todas
  as rodadas junto com preâmbulos mais curtos que nunca (camada 1: mediana 12,5 palavras).
- A vantagem de accuracy da iter-3 (0,90 vs 0,875) é de 3 casos em 120 — dentro do ruído —
  e veio ao custo da conversa quebrada.

## Diagnóstico de encerramento: whack-a-mole no limite do 4B

Cada lote dirigido (012→015) fechou 100% dos seus alvos e deslocou 2-3 casos vizinhos:
o batch_013 fechou "é fixo"/punt e derrubou a conversa; o 014 restaurou a conversa e o punt
voltou; o 015 fechou o punt e a Selic regrediu ("pouca volatilidade, é 11,25%" — alucinação).
Oscilação de ±3/120 entre rodadas = ruído. Mais dados nesta escala não compram melhoria
líquida; parar aqui foi decisão deliberada, não desistência.

## Limitações conhecidas da versão final (documentar, não corrigir)

1. **ws-008 (Selic)**: voltou a responder de memória com valor desatualizado.
2. **`import math`**: py-016 agora usa `math.sin`/`math.pi` (aprendeu o vocabulário do
   batch_015) mas omite a linha `import math` no primeiro tiro. MITIGADO pelo harness:
   `inference_loop.py` executa o código de verdade, devolve o stderr (NameError) como
   turno `tool` e permite até 3 iterações — o modelo foi treinado (imperfect_tool) a
   corrigir e re-executar. A eval da Fase 4 é single-shot e não captura essa recuperação;
   verificar na demo Fase 5 (pergunta do projétil) se a autocorreção acontece na prática.
3. **Demo do cálculo**: escolheu `int(0.375*18420)` → 6907, truncando o 6907,5 correto.
4. **Resposta do dólar**: cita o valor certo da fonte, mas inventou causa ("alta do
   petróleo") que não estava no snippet — confabulação leve pós-busca.
5. **python_sandbox recall 0,80**: 4 misses em 20 (responde direto sem verificar).

## Estado final dos artefatos

- **Dataset**: 443 exemplos (batches 001–015 + pilot), 443/443 na validação,
  `data/clean/dataset.jsonl` versionado. Distribuição: 0=16,7%, 0.5=12%, 1=28,9%,
  2=18,3%, 3=5,4%, C=18,7%.
- **Histórico completo** dos lotes em `data/raw/GEN_PROGRESS.md`.
- **⚠️ AÇÃO PENDENTE — persistir o adapter**: `outputs/adapter_4b` da iter-5 vive SÓ na VM
  do Colab (outputs/ é ignorado no git). Antes de encerrar a sessão do Colab: baixar o zip
  do adapter OU dar push pro HF Hub (`model.push_to_hub`). Sem isso, a versão final se
  perde e exige retreino (reproduzível: dataset + notebook estão versionados, <1 crédito).
