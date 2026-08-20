def test_structured_contacts_contract_marker():
    from actions.contacts import create_contact
    assert callable(create_contact)
