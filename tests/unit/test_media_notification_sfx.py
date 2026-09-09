from actions import media


def test_media_notification_sfx_uses_eva_callback():
    calls = []
    media.set_media_notification_sfx(lambda: calls.append("done"))

    media._play_background_notification_sfx()

    assert calls == ["done"]


def test_media_notification_sfx_is_noop_without_callback():
    media.set_media_notification_sfx(None)

    media._play_background_notification_sfx()
