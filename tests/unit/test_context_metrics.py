from core.config import _log_live_context_metrics


def test_live_context_metrics_reports_system_memory_and_tools(capsys, monkeypatch):
    monkeypatch.delenv("EVA_CONTEXT_METRICS", raising=False)

    _log_live_context_metrics(
        {
            "system_instruction": (
                "[İSTİFADƏÇİ HAQQINDA MƏLUMATLAR]\n"
                "  preferences/name: Abdulla\n\n"
                "Sən EVA-san — test prompt."
            ),
            "tools": [
                {
                    "function_declarations": [
                        {"name": "tool_a", "description": "A"},
                        {"name": "tool_b", "description": "B"},
                    ]
                }
            ],
        }
    )

    output = capsys.readouterr().out

    assert "[CONTEXT]" in output
    assert "system=" in output
    assert "memory=" in output
    assert "tools=2 declarations/" in output
    assert "total=" in output
    assert "[CONTEXT-TOOLS] top10:" in output
    assert "tool_a=" in output
    assert "tool_b=" in output


def test_live_context_metrics_orders_largest_tools_first(capsys, monkeypatch):
    monkeypatch.delenv("EVA_CONTEXT_METRICS", raising=False)

    _log_live_context_metrics(
        {
            "system_instruction": "test",
            "tools": [
                {
                    "function_declarations": [
                        {"name": "small", "description": "x"},
                        {"name": "large", "description": "x" * 200},
                    ]
                }
            ],
        }
    )

    output = capsys.readouterr().out
    top_line = next(line for line in output.splitlines() if line.startswith("[CONTEXT-TOOLS]"))

    assert top_line.index("large=") < top_line.index("small=")


def test_live_context_metrics_can_be_disabled(capsys, monkeypatch):
    monkeypatch.setenv("EVA_CONTEXT_METRICS", "false")

    _log_live_context_metrics({"system_instruction": "test", "tools": []})

    assert capsys.readouterr().out == ""
