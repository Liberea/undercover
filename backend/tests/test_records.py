import pytest


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["trip"]["trip_cost"] == 3100.0
    assert policy["travelers"] == ["Maya Patel"]


def test_get_claim_history(client):
    history = client.get("/api/customers/CUS-3001/claims").json()
    assert history["name"] == "Maya Patel"
    assert [c["claim_id"] for c in history["previous_claims"]] == ["CLM-0412"]
    assert set(history) == {"customer_id", "name", "customer_since", "previous_claims"}


@pytest.mark.parametrize(
    ("path", "detail"),
    [
        ("/api/policies/POL-9999", "Policy POL-9999 not found"),
        ("/api/customers/CUS-9999/claims", "Customer CUS-9999 not found"),
    ],
)
def test_unknown_records(client, path, detail):
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {"detail": detail}


def test_list_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert [h["name"] for h in handlers] == [
        "Dana Whitfield",
        "Marcus Oyelaran",
        "Priya Raman",
    ]


def test_get_policy_wording(client):
    text = client.get("/api/policy-wording").json()["text"]
    assert text.startswith("# UnderCover Travel Insurance: Policy Wording")
