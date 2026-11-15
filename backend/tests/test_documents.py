import pytest


def contents(client, document):
    return client.get(f"/api/documents/{document}/sections").json()


def test_list_sections_of_the_policy_wording(client):
    sections = contents(client, "policy_wording")
    assert [s["section"] for s in sections] == list(range(1, 13))
    assert sections[2] == {"section": 3, "title": "Trip Delay", "topics": []}
    assert sections[7]["topics"] == [
        "Adventure Sports",
        "Pre-Existing Condition Waiver",
        "Electronics Plus",
    ]


def test_list_sections_of_the_claims_manual(client):
    sections = contents(client, "claims_manual")
    assert [s["section"] for s in sections] == list(range(1, 15))
    assert sections[6]["title"] == "Interpretation notes"
    assert "Wild animals" in sections[6]["topics"]


def test_read_section(client):
    section = client.get("/api/documents/claims_manual/sections/9").json()
    assert section["document"] == "claims_manual"
    assert section["section"] == 9
    assert section["title"] == "Repeat claims"
    assert section["text"].startswith("Before deciding any claim")
    assert "## 10." not in section["text"]


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        ("/api/documents/handbook/sections", "Document handbook not found"),
        ("/api/documents/handbook/sections/1", "Document handbook not found"),
        (
            "/api/documents/claims_manual/sections/99",
            "Section 99 of claims_manual not found",
        ),
    ],
)
def test_unknown_document_or_section(client, path, detail):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {"detail": detail}
