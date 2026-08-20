def test_contacts_structured_result_ci_import():
    from core.results import make_result
    assert make_result("contact", "success")["type"] == "contact"
