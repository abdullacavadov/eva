from integrations.google.gmail import folder_query


def test_gmail_folder_queries_map_to_distinct_scopes():
    expected = {
        "inbox": "in:inbox",
        "sent": "in:sent",
        "drafts": "in:drafts",
        "spam": "in:spam",
        "trash": "in:trash",
        "promotions": "category:promotions",
        "social": "category:social",
        "updates": "category:updates",
        "purchases": "category:purchases",
        "starred": "is:starred",
        "all_mail": "-in:spam -in:trash",
    }

    assert {folder: folder_query(folder) for folder in expected} == expected


def test_gmail_folder_query_rejects_unknown_scope():
    try:
        folder_query("unknown")
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("Unknown Gmail folder must be rejected")
