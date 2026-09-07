from actions import browser


def test_youtube_lookup_hides_exception_details(monkeypatch):
    monkeypatch.setattr(
        browser,
        "_find_first_youtube_video",
        lambda _: (_ for _ in ()).throw(RuntimeError("C:\\Users\\secret-user\\private-token")),
    )
    opened = []
    monkeypatch.setattr(browser, "_open", opened.append)

    result = browser.browser_control("play_youtube", query="test")

    assert "secret-user" not in result
    assert "private-token" not in result
    assert "YouTube ilk nəticəsi alınmadı." in result
    assert opened == ["https://www.youtube.com/results?search_query=test"]
