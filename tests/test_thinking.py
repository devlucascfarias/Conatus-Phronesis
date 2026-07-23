import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from common import preamble_text, strip_think_blocks, think_format_error, think_text, word_count


def test_preamble_ignores_thinking_before_tool_call():
    content = (
        "<think>\nDeliberação extensa que não entra na métrica.\n</think>\n\n"
        "Verificação curta.\n<tool_call>\n"
        '{"name":"python_sandbox","arguments":{"code":"print(1)"}}\n'
        "</tool_call>"
    )
    assert preamble_text(content) == "Verificação curta."


def test_preamble_ignores_thinking_before_visible_answer():
    content = "<think>\nEscolha do método.\n</think>\n\nPrimeiro parágrafo.\n\nSegundo."
    assert preamble_text(content) == "Primeiro parágrafo."


def test_truncated_thinking_is_not_counted_as_visible_preamble():
    assert strip_think_blocks("<think>\nRaciocínio truncado") == ""


def test_think_format_accepts_a_tool_call_only_after_closing_tag():
    content = (
        "<think>\nPreciso verificar numericamente.\n</think>\n\n"
        '<tool_call>\n{"name":"python_sandbox","arguments":{"code":"print(1)"}}\n</tool_call>'
    )
    assert think_format_error(content) is None


def test_think_format_rejects_tool_call_inside_reasoning():
    content = (
        "<think>\n"
        '<tool_call>\n{"name":"python_sandbox","arguments":{"code":"print(1)"}}\n</tool_call>\n'
        "</think>"
    )
    assert think_format_error(content) == "tool_call_dentro_do_think"


def test_think_format_rejects_malformed_or_empty_blocks():
    assert think_format_error("texto\n<think>\nrazão\n</think>") == "bloco_think_malformado"
    assert think_format_error("<think>\n\n</think>") == "bloco_think_vazio"


def test_think_text_supports_layer_word_limits():
    content = "<think>\nDecisão curta, específica e verificável.\n</think>\n\nResposta."
    assert think_text(content) == "Decisão curta, específica e verificável."
    assert word_count(think_text(content)) == 5
