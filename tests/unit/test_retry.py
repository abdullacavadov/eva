import pytest

from core.retry import is_transient_error, retry_read


class TimeoutErrorForTest(Exception):
    pass


class HttpError429(Exception):
    status_code = 429


def test_transient_timeout_is_retryable():
    assert is_transient_error(TimeoutErrorForTest("timeout")) is True


def test_rate_limit_is_retryable():
    assert is_transient_error(HttpError429("too many requests")) is True


def test_validation_error_is_not_retryable():
    assert is_transient_error(ValueError("invalid request")) is False


def test_retry_read_uses_exponential_backoff_for_transient_errors():
    calls = []
    sleeps = []

    def operation():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutErrorForTest("timeout")
        return "ok"

    assert retry_read(operation, attempts=3, base_delay=0.1, sleep=sleeps.append) == "ok"
    assert len(calls) == 3
    assert sleeps == [0.1, 0.2]


def test_retry_read_does_not_retry_non_transient_errors():
    calls = []
    sleeps = []

    def operation():
        calls.append(1)
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        retry_read(operation, attempts=3, sleep=sleeps.append)

    assert len(calls) == 1
    assert sleeps == []
