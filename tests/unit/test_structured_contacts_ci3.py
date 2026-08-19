def test_contacts_structured_result_module():
    from core.results import make_result
    result = make_result("contact", "success", data=[])
    assert result["type"] == "contact"
    assert result["status"] == "success"
    assert result["count"] == 0
