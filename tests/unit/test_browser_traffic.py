from actions import browser


def test_traffic_opens_google_maps(monkeypatch):
    opened = []
    monkeypatch.setattr(browser, "_open", opened.append)
    result = browser.browser_control("traffic", query="Bakı -> Gəncə")
    assert opened
    assert opened[0].startswith("https://www.google.com/maps/dir/?")
    assert "Bakı" in result
    assert "Gəncə" in result


def test_city_traffic_opens_live_map(monkeypatch):
    opened = []
    monkeypatch.setattr(browser, "_open", opened.append)
    result = browser.browser_control("traffic", query="Bakı")
    assert opened
    assert opened[0].startswith("https://www.google.com/maps/search/?")
    assert "canlı" in result.lower()


# Şəhər sorğusu route tələb etmir; canlı trafik görünüşü açılır.
