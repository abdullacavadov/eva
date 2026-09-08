import pytest

from core.media_image import _explain_gemini_image_error


def test_gemini_billing_disabled_is_explained_clearly():
    message = _explain_gemini_image_error(Exception("403 BILLING_NOT_ENABLED: billing is not enabled"))
    assert "aktiv billing hesabı yoxdur" in message
    assert "billing" in message.lower()


def test_gemini_insufficient_balance_is_explained_clearly():
    message = _explain_gemini_image_error(Exception("payment failed: insufficient balance"))
    assert "balans" in message.lower()
    assert "ödəniş" in message.lower()


def test_gemini_quota_error_is_explained_clearly():
    message = _explain_gemini_image_error(Exception("429 RESOURCE_EXHAUSTED"))
    assert "quota" in message.lower()
    assert "Gemini" in message


def test_gemini_unknown_error_keeps_original_reason():
    message = _explain_gemini_image_error(Exception("model unavailable"))
    assert "model unavailable" in message
