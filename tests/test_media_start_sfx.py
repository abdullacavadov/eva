from actions import media


def test_media_start_notification_uses_victor_done_sfx():
    calls = []
    media.set_media_notification_sfx(lambda: calls.append("done"))

    media._play_background_notification_sfx()

    assert calls == ["done"]
