from core.tool_executor import _present_structured_result


class FakeUI:
    def __init__(self):
        self.messages = []

    def write_log(self, message):
        self.messages.append(message)


def test_present_structured_result_renders_unified_items():
    ui = FakeUI()
    result = {
        "type": "calendar",
        "status": "success",
        "data": [
            {"title": "Komanda görüşü", "start_iso": "2026-09-05T10:00:00+04:00"},
            {"title": "Layihə görüşü", "start": "2026-09-05T14:00:00+04:00", "status": "confirmed"},
        ],
        "count": 2,
    }

    _present_structured_result(ui, result)

    assert ui.messages[0] == "SYS: CALENDAR nəticəsi (2):"
    assert "1. Komanda görüşü — 2026-09-05T10:00:00+04:00" in ui.messages
    assert "2. Layihə görüşü — 2026-09-05T14:00:00+04:00 | confirmed" in ui.messages


def test_present_structured_result_handles_empty_data():
    ui = FakeUI()

    _present_structured_result(ui, {"type": "task", "status": "success", "data": []})

    assert ui.messages == ["SYS: Nəticə tapılmadı."]


def test_present_structured_result_ignores_non_success_results():
    ui = FakeUI()

    _present_structured_result(ui, {"type": "calendar", "status": "error", "data": [{"title": "Test"}]})

    assert ui.messages == []
