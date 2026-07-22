---
license: apache-2.0
base_model: Qwen/Qwen3-4B-Instruct-2507
tags:
  - qlora
  - peft
  - lora
  - tool-use
  - function-calling
  - qwen3
  - portuguese
  - pt-BR
language:
  - pt
  - en
library_name: peft
pipeline_tag: text-generation
---

# Qwen3-4B — Tool-Use Judgment (QLoRA)

Adapter LoRA para **[Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)**
treinado para exercer **critério** sobre quando usar ferramentas — não apenas o formato do
tool call (que o modelo base já sabe), mas a decisão: buscar na web quando o dado é volátil
ou local, verificar no sandbox Python quando o cálculo é verificável, ou simplesmente
responder quando a pergunta é trivial ou conversacional.

## Detalhes do modelo

- **Modelo base:** Qwen/Qwen3-4B-Instruct-2507
- **Método:** SFT com QLoRA (4-bit), via [Unsloth](https://github.com/unslothai/unsloth) + TRL
- **Idiomas:** português (pt-BR, ~85% do dataset) e inglês (~15%)
- **Ferramentas:** `web_search(query)`, `python_sandbox(code)`
- **Licença:** apache-2.0 (herdada do modelo base)

## Como usar

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base = "Qwen/Qwen3-4B-Instruct-2507"
tokenizer = AutoTokenizer.from_pretrained(base)
model = AutoModelForCausalLM.from_pretrained(base, torch_dtype="auto", device_map="auto")
model = PeftModel.from_pretrained(model, "devlucascfarias/qwen3-4b-tool-judgment")
model.eval()

tools = [
    {"type": "function", "function": {"name": "web_search", "description": "Busca na web",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "python_sandbox", "description": "Executa Python",
     "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
]

messages = [{"role": "user", "content": "Quanto tá o dólar hoje?"}]
prompt = tokenizer.apply_chat_template(messages, tools=tools, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
out = model.generate(**inputs, max_new_tokens=512, do_sample=False, no_repeat_ngram_size=8,
                      pad_token_id=tokenizer.eos_token_id)
print(tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True))
```

**Importante — decodificação:** use `do_sample=False` com `no_repeat_ngram_size=8`. Em testes,
`do_sample=True` com temperatura alta introduziu variância indesejada em respostas de cálculo
e raciocínio (o modelo sorteava versões diferentes do mesmo erro a cada geração); guloso puro
sem bloqueio de repetição pode entrar em loop em respostas longas e abertas (ex.: curiosidades).

Um harness de referência completo — que executa `python_sandbox` de verdade (com injeção
automática de imports ausentes da whitelist: `math`, `numpy`, `sympy`, etc.) e `web_search`
via Ollama/Tavily/DuckDuckGo — está disponível no repositório do projeto
([`inference_loop.py`](https://github.com/devlucascfarias/Conatus-Phronesis)).

## Dados de treino

443 exemplos gerados sinteticamente (com filtros programáticos + execução real de código
de verificação), distribuídos em 6 camadas de comportamento-alvo:

| Camada | Descrição | Share |
|---|---|---|
| 0 | Trivial — resposta direta, zero preâmbulo, sem tool | 16,7% |
| 0.5 | Fronteiriça — parece exigir busca, mas é estável; rationale curto de *não* buscar | 12,0% |
| 1 | Volátil/local/incerteza própria — rationale + `web_search` + resposta citando o resultado | 28,9% |
| 2 | Cálculo verificável — resolução compacta + `python_sandbox` + confirmação/autocorreção | 18,3% |
| 3 | Genuinamente difícil — raciocínio longo, com ou sem tool | 5,4% |
| C | Conversa natural — papo, opinião, criatividade curta, sem tool | 18,7% |

Passou por 5 rodadas de refinamento dirigido por análise de erro (ver histórico completo no
repositório: `data/raw/GEN_PROGRESS.md` e `STATUS_FINAL.md`).

## Avaliação

Eval em 120 casos hold-out (40 web_search / 20 python_sandbox / 60 none), decodificação
gulosa, comparando a decisão de tool prevista contra a esperada:

| Métrica | Baseline (modelo base) | **Este adapter** |
|---|---|---|
| Accuracy | 0,850 | **0,875** |
| web_search F1 | 0,833 | **0,841** |
| web_search precision | — | **1,000** |
| python_sandbox recall | 0,700 | 0,800 |
| Falso positivo (busca em pergunta trivial) | 3,3% | **0,0%** |
| JSON de tool call válido | — | 1,000 |

O adapter supera o baseline em toda métrica relevante e elimina os dois modos de falha
qualitativos mais visíveis do baseline: **"punt"** (mandar o usuário conferir num site em
vez de buscar) e **assumir que dado local/volátil é fixo** (ex.: horário de museu, taxa Selic).

## Limitações conhecidas

- **Erros semânticos que executam com sucesso** não são pegos por nenhum checker
  determinístico: fórmula matemática incorreta que roda sem exceção, arredondamento/
  truncamento inconsistente entre gerações, leitura errada de magnitude do resultado de
  uma tool. É o teto esperado de um modelo 4B treinado com ~450 exemplos — não um bug do
  dataset ou do harness.
- **Confabulação leve pós-busca**: o modelo às vezes anexa uma causa ou detalhe plausível
  mas não presente no resultado da busca (ex.: atribuir a variação do dólar ao petróleo
  quando a fonte não menciona isso).
- **Cobertura de tópicos "resultado que acho que sei"** (loterias, prêmios, realities) foi
  reforçada mas não é exaustiva — categorias muito fora do padrão de treino podem ainda
  induzir uma resposta de memória em vez de busca.
- Testado apenas em português (pt-BR) e inglês; não avaliado em outros idiomas.

## Framework versions

- PEFT 0.19.1
- Transformers (via Unsloth)
- TRL (SFTTrainer)
