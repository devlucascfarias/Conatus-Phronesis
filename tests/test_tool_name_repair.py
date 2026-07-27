"""Reparo de nome de tool alucinado (item 5 do plano de correção de 2026-07-26).

Os nomes testados aqui não são inventados para o teste: `python_sandro`, `python_sandox`,
`python_jupyter_cell`, `python_eval`, `python_print` e `python` foram todos observados de
verdade no 8B treinado e estão registrados em data/eval/thinking_8b_eval_notes.md — quatro
variações distintas só na rodada com sampling.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inference_loop import repair_tool_name


def _call(name, args):
    return {"name": name, "arguments": args}


# --- nomes válidos passam intactos ----------------------------------------------------

def test_nome_valido_nao_e_tocado():
    for nome, args in [("python_sandbox", {"code": "print(1)"}),
                       ("web_search", {"query": "dolar hoje"})]:
        call, alucinado = repair_tool_name(_call(nome, args))
        assert alucinado is None
        assert call["name"] == nome


# --- alucinações reais, todas com argumento `code` ------------------------------------

def test_variacoes_alucinadas_viram_python_sandbox():
    """Todas as variações observadas levavam `code` — a assinatura resolve sozinha."""
    for nome in ["python_sandro", "python_sandox", "python_jupyter_cell",
                 "python_eval", "python_print", "python", "sandbox", "exec_python"]:
        call, alucinado = repair_tool_name(_call(nome, {"code": "print(2+2)"}))
        assert call["name"] == "python_sandbox", f"{nome} não foi reparado"
        assert alucinado == nome


def test_alucinacao_de_busca_vira_web_search():
    for nome in ["search", "web_lookup", "buscar_web", "google_search"]:
        call, alucinado = repair_tool_name(_call(nome, {"query": "cotação do dólar"}))
        assert call["name"] == "web_search", f"{nome} não foi reparado"
        assert alucinado == nome


# --- a assinatura tem prioridade sobre a semelhança de nome ---------------------------

def test_assinatura_vence_nome_enganoso():
    """Nome parece busca, mas os argumentos são de sandbox — os argumentos mandam."""
    call, alucinado = repair_tool_name(_call("web_search_python", {"code": "print(1)"}))
    assert call["name"] == "python_sandbox"
    assert alucinado == "web_search_python"


# --- fallback por semelhança quando não há assinatura utilizável ----------------------

def test_erro_de_digitacao_sem_argumento_util():
    call, alucinado = repair_tool_name(_call("python_sandbx", {}))
    assert call["name"] == "python_sandbox"
    assert alucinado == "python_sandbx"


def test_nome_irreconhecivel_fica_intacto():
    """Sem assinatura e sem semelhança, o erro tem de subir — não inventar um destino."""
    call, alucinado = repair_tool_name(_call("enviar_email", {"para": "x@y.com"}))
    assert call["name"] == "enviar_email"
    assert alucinado is None


def test_argumentos_nao_dict_nao_quebram():
    call, alucinado = repair_tool_name(_call("python_qualquer", "string solta"))
    assert call["name"] == "python_qualquer"
    assert alucinado is None


# --- o reparo não pode vazar para a validação de dataset ------------------------------

def test_validador_continua_reprovando_nome_invalido():
    """O dado de TREINO tem de ser estrito: reparar ali esconderia exemplo ruim."""
    from validate_data import check_schema, tool_schemas
    schemas = tool_schemas()
    assert check_schema(_call("python_sandro", {"code": "print(1)"}), schemas) == \
        "tool_desconhecida:python_sandro"
