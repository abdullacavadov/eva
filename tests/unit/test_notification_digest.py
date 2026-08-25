from core.notification_digest import build_notification_digest


def test_digest_groups_pending_events_by_source():
    pending = {
        "w1": {"key": "w1", "source": "whatsapp", "item": {"id": "1"}},
        "w2": {"key": "w2", "source": "whatsapp", "item": {"id": "2"}},
        "g1": {"key": "g1", "source": "gmail", "item": {"id": "3"}},
    }

    digest = build_notification_digest(pending)

    assert digest["source"] == "digest"
    assert digest["count"] == 3
    assert digest["counts"] == {"whatsapp": 2, "gmail": 1}
    assert "WhatsApp: 2" in digest["text"]
    assert "Gmail: 1" in digest["text"]


def test_empty_pending_has_no_digest():
    assert build_notification_digest({}) is None


def test_digest_keeps_original_events_for_follow_up():
    pending = {
        "g1": {"key": "g1", "source": "gmail", "item": {"subject": "Test"}},
    }

    digest = build_notification_digest(pending)

    assert digest["items"] == list(pending.values())
