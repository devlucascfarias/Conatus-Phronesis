"""Grounding pós-tool (item 4 do plano de correção de 2026-07-26).

Cada caso abaixo é um bug REAL observado no 8B treinado, registrado em
data/eval/thinking_8b_eval_notes.md — ou o contra-caso legítimo que não pode ser
reprovado junto. Se um destes quebrar, o filtro parou de proteger contra o modo de
falha que motivou sua existência.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from validate_data import answer_numbers, check_answer_echoes_tool, check_websearch_grounding


def _ex(msgs, layer="2"):
    return {"layer": layer, "lang": "pt-BR", "messages": msgs}


def _sandbox_turn(code):
    return {
        "role": "assistant",
        "content": (
            "<think>\ncalculando\n</think>\n\n<tool_call>\n"
            f'{{"name": "python_sandbox", "arguments": {{"code": "{code}"}}}}\n'
            "</tool_call>"
        ),
    }


def _ws_turn(query="dolar hoje"):
    return {
        "role": "assistant",
        "content": (
            "<think>\nbuscar\n</think>\n\n<tool_call>\n"
            f'{{"name": "web_search", "arguments": {{"query": "{query}"}}}}\n'
            "</tool_call>"
        ),
    }


WS_DOLAR = (
    '{"results": [{"title": "Dólar hoje", "url": "https://x.com", '
    '"snippet": "Dólar fechou em R$ 5,08 nesta sexta."}]}'
)
WS_JUROS = (
    '{"results": [{"title": "Juros", "url": "https://x.com", '
    '"snippet": "Taxa de 1,15% ao mês; CDI rende 0,85% ao mês."}]}'
)


# --- stdout de valor único ------------------------------------------------------------

def test_corrupcao_de_valor_unico_e_rejeitada():
    """Bug real (rodada sampling): sandbox devolveu 6907.5 e a resposta escreveu 6.906,75."""
    ex = _ex([
        {"role": "user", "content": "Quanto é 37,5% de 18.420?"},
        _sandbox_turn("print(3*18420/8)"),
        {"role": "tool", "content": "6907.5"},
        {"role": "assistant", "content": "<think>\nconfere\n</think>\n\nSão **R$ 6.906,75**."},
    ])
    assert check_answer_echoes_tool(ex) == "resposta_nao_ecoa_resultado_tool"


def test_valor_unico_com_conversao_de_moeda_passa():
    ex = _ex([
        {"role": "user", "content": "Quanto é 37,5% de 18.420?"},
        _sandbox_turn("print(3*18420/8)"),
        {"role": "tool", "content": "6907.5"},
        {"role": "assistant", "content": "<think>\nconfere\n</think>\n\nSão **R$ 6.907,50**."},
    ])
    assert check_answer_echoes_tool(ex) is None


# --- stdout multi-valor: o buraco que o item 4 fechou ---------------------------------

def test_multi_valor_com_numero_fabricado_e_rejeitado():
    """Bug real (item 10 do held-out): stdout trouxe 2994 e a resposta usou 1994.

    Antes do item 4 este caso passava batido — `len(tool_nums) != 1` desistia do check.
    """
    ex = _ex([
        {"role": "user", "content": "Quantos falsos positivos?"},
        _sandbox_turn("print(2994, 6, 99800)"),
        {"role": "tool", "content": "2994 6 99800"},
        {"role": "assistant", "content": "<think>\nsao 1994\n</think>\n\nSão **1994** falsos positivos."},
    ])
    assert check_answer_echoes_tool(ex) == "resposta_nao_ecoa_nenhum_valor_do_tool"


def test_multi_valor_citando_valor_real_passa():
    ex = _ex([
        {"role": "user", "content": "Quantos falsos positivos?"},
        _sandbox_turn("print(2994, 6, 99800)"),
        {"role": "tool", "content": "2994 6 99800"},
        {"role": "assistant", "content": "<think>\nok\n</think>\n\nSão **2994** falsos positivos."},
    ])
    assert check_answer_echoes_tool(ex) is None


def test_multi_valor_com_conversao_percentual_passa():
    """stdout imprime a fração 0.25 e a resposta diz "25%" — conversão, não fabricação."""
    ex = _ex([
        {"role": "user", "content": "Qual a eficiência?"},
        _sandbox_turn("print(2.0, 1.0, 0.25)"),
        {"role": "tool", "content": "2.0 1.0 0.25"},
        {"role": "assistant", "content": "<think>\nok\n</think>\n\nA eficiência é **25%**."},
    ])
    assert check_answer_echoes_tool(ex) is None


def test_traceback_nao_exige_eco():
    """Episódio de debug (batch_027): a resposta discute a causa do erro, não ecoa números."""
    ex = _ex([
        {"role": "user", "content": "Calcule"},
        _sandbox_turn("print(undefined_var)"),
        {"role": "tool", "content": "NameError: name 'undefined_var' is not defined"},
        {"role": "assistant", "content": "<think>\nvariavel nao definida\n</think>\n\nO erro foi variável não definida."},
    ])
    assert check_answer_echoes_tool(ex) is None


# --- tipografia numérica do LaTeX -----------------------------------------------------

def test_separador_de_milhar_latex_nao_fragmenta_numero():
    """\\, entre dígitos é espaço fino, não separador de números distintos."""
    assert 355687428096000.0 in answer_numbers(r"17!=355\,687\,428\,096\,000")


def test_virgula_decimal_latex_e_lida():
    """{,} é a vírgula decimal em LaTeX; sem normalizar viraria dois números."""
    assert 1.0995 in answer_numbers(r"\(1{,}0995\times10^{12}\)")


def test_inteiro_grande_bem_tipografado_ecoa_o_stdout():
    """Regressão: 17! escrito com espaço fino reprovava por engano (visto no batch_029)."""
    ex = _ex([
        {"role": "user", "content": "What is 17!?"},
        _sandbox_turn("import math\\nprint(math.factorial(17))"),
        {"role": "tool", "content": "355687428096000"},
        {"role": "assistant", "content": "<think>\nok\n</think>\n\n\\(17!=355\\,687\\,428\\,096\\,000\\)."},
    ])
    assert check_answer_echoes_tool(ex) is None


# --- grounding de busca ---------------------------------------------------------------

def test_cotacao_fabricada_e_rejeitada():
    """Bug real: 'compra R$ 5,0801 / venda R$ 5,0907' citado sem estar em nenhum snippet."""
    ex = _ex([
        {"role": "user", "content": "Quanto tá o dólar?"},
        _ws_turn(),
        {"role": "tool", "content": WS_DOLAR},
        {"role": "assistant", "content": "<think>\nok\n</think>\n\nCompra R$ 5,0801 e venda R$ 5,0907."},
    ], layer="1")
    assert check_websearch_grounding(ex) == "resposta_numero_nao_grounded_em_busca"


def test_cotacao_citada_da_busca_passa():
    ex = _ex([
        {"role": "user", "content": "Quanto tá o dólar?"},
        _ws_turn(),
        {"role": "tool", "content": WS_DOLAR},
        {"role": "assistant", "content": "<think>\nok\n</think>\n\nO dólar está em R$ 5,08."},
    ], layer="1")
    assert check_websearch_grounding(ex) is None


# --- conversa mista (busca + sandbox) -------------------------------------------------

def test_mista_com_aritmetica_derivada_passa():
    """R$ 1.600 é 5882.88 - 4276.25 arredondado — derivação legítima, não citação.

    Regime leniente: em conversa mista só reprovamos quando NENHUM número tem origem.
    """
    ex = _ex([
        {"role": "user", "content": "Quito ou invisto?"},
        _ws_turn("juros financiamento"),
        {"role": "tool", "content": WS_JUROS},
        _sandbox_turn("print(5882.88, 4276.25)"),
        {"role": "tool", "content": "5882.88 4276.25"},
        {"role": "assistant", "content": (
            "<think>\nok\n</think>\n\nA 1,15% ao mês custa R$ 5.883 contra R$ 4.276 "
            "do CDI — economia de cerca de R$ 1.600."
        )},
    ], layer="3")
    assert check_websearch_grounding(ex) is None


def test_mista_com_tudo_fabricado_e_rejeitada():
    ex = _ex([
        {"role": "user", "content": "Quito ou invisto?"},
        _ws_turn("juros financiamento"),
        {"role": "tool", "content": WS_JUROS},
        _sandbox_turn("print(5882.88, 4276.25)"),
        {"role": "tool", "content": "5882.88 4276.25"},
        {"role": "assistant", "content": (
            "<think>\nok\n</think>\n\nA taxa é 3,47% ao mês contra 9,91% — "
            "diferença de R$ 71,23."
        )},
    ], layer="3")
    assert check_websearch_grounding(ex) == "resposta_numero_nao_grounded_em_busca"
