from core.proactive_audio import ProactiveAudioPolicy


def test_audio_disabled_never_speaks():
    policy = ProactiveAudioPolicy(enabled=False)
    assert policy.should_speak(speaking=False, muted=False, paused=False) is False


def test_audio_does_not_interrupt_eva_speaking():
    policy = ProactiveAudioPolicy()
    assert policy.should_speak(speaking=True, muted=False, paused=False) is False


def test_audio_can_interrupt_only_when_explicitly_enabled():
    policy = ProactiveAudioPolicy(interrupt_speaking=True)
    assert policy.should_speak(speaking=True, muted=False, paused=False) is True


def test_audio_respects_mute_and_pause():
    policy = ProactiveAudioPolicy()
    assert policy.should_speak(speaking=False, muted=True, paused=False) is False
    assert policy.should_speak(speaking=False, muted=False, paused=True) is False


def test_audio_text_prefers_notification_text():
    policy = ProactiveAudioPolicy()
    assert policy.choose_text({"text": "Yeni email gəldi", "title": "Email"}) == "Yeni email gəldi"
