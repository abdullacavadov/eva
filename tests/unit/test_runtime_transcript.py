from main import JarvisLive


def test_control_tokens_are_not_treated_as_runtime_error_noise():
    text, had_noise = JarvisLive._clean_transcript_text("<ctrl1><ctrl2>")
    assert text == ""
    assert had_noise is False


def test_real_control_free_text_remains_unchanged():
    text, had_noise = JarvisLive._clean_transcript_text("Email hazırlanıb.")
    assert text == "Email hazırlanıb."
    assert had_noise is False
