from contextlib import closing

import pytest

from backend.db import connect

LIMIT_MESSAGE = "A payout over $1,000.00 needs a handler's sign-off."


def start(client, claim_id):
    return client.post(f"/api/claims/{claim_id}/start", json={"thread_id": "t-1"})


def decide(client, claim_id, outcome, payout):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "outcome": outcome,
            "payout": payout,
            "reasons": "The delay is covered.",
            "policy_section": "Section 3, Trip Delay",
        },
    )


def pay(client, claim_id, amount):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, claim_id, handler_id):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def approved(client, claim_id, payout):
    start(client, claim_id)
    return decide(client, claim_id, "approve", payout)


def test_start_claim(client):
    claim = start(client, "CLM-1001").json()
    assert claim["status"] == "in_progress"
    assert claim["thread_id"] == "t-1"


def test_start_claim_again_after_a_failed_run(client):
    start(client, "CLM-1001")
    assert start(client, "CLM-1001").status_code == 200


def test_release_claim(client):
    start(client, "CLM-1001")
    response = client.post("/api/claims/CLM-1001/release")
    assert response.json()["status"] == "waiting"


def test_release_waiting_claim(client):
    response = client.post("/api/claims/CLM-1001/release")
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1001 is waiting"}


def test_approve_under_limit_and_pay(client):
    claim = approved(client, "CLM-1001", 420).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["outcome"] == "approve"
    assert claim["decision"]["payment"] is None
    payment = pay(client, "CLM-1001", 420).json()["decision"]["payment"]
    assert payment["amount"] == 420
    assert payment["signed_off_by"] is None


def test_approve_over_limit_waits_for_sign_off(client):
    assert approved(client, "CLM-1002", 1150).json()["status"] == "waiting_for_sign_off"
    response = pay(client, "CLM-1002", 1150)
    assert response.status_code == 403
    assert response.json() == {"detail": LIMIT_MESSAGE}
    assert client.get("/api/claims/CLM-1002").json()["decision"]["payment"] is None


def test_sign_off_pays(client):
    approved(client, "CLM-1002", 1150)
    claim = sign_off(client, "CLM-1002", "HND-01").json()
    assert claim["status"] == "decided"
    assert claim["decision"]["payment"]["amount"] == 1150
    assert claim["decision"]["payment"]["signed_off_by"] == "Dana Whitfield"
    response = pay(client, "CLM-1002", 1150)
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1002 is already paid"}


def test_payout_at_the_limit_needs_no_sign_off(client):
    assert approved(client, "CLM-1002", 1000).json()["status"] == "decided"
    assert pay(client, "CLM-1002", 1000).status_code == 200


@pytest.mark.parametrize("outcome", ["decline", "refer"])
def test_decline_and_refer_are_decided(client, outcome):
    start(client, "CLM-1001")
    claim = decide(client, "CLM-1001", outcome, 0).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["outcome"] == outcome


def test_decide_claim_not_in_progress(client):
    response = decide(client, "CLM-1001", "approve", 420)
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1001 is waiting"}


@pytest.mark.parametrize(
    ("outcome", "payout"), [("decline", 50), ("refer", 10), ("pay", 0), ("approve", -1)]
)
def test_invalid_decisions(client, outcome, payout):
    start(client, "CLM-1001")
    assert decide(client, "CLM-1001", outcome, payout).status_code == 422


def test_pay_without_approval(client):
    start(client, "CLM-1001")
    decide(client, "CLM-1001", "decline", 0)
    response = pay(client, "CLM-1001", 420)
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1001 has no approval to pay"}


def test_pay_a_different_amount(client):
    approved(client, "CLM-1001", 420)
    response = pay(client, "CLM-1001", 500)
    assert response.status_code == 409
    assert response.json() == {"detail": "The approved payout is $420.00, not $500.00"}


def test_sign_off_claim_not_waiting_for_sign_off(client):
    approved(client, "CLM-1001", 420)
    response = sign_off(client, "CLM-1001", "HND-01")
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1001 is decided"}


def test_sign_off_by_unknown_handler(client):
    approved(client, "CLM-1002", 1150)
    response = sign_off(client, "CLM-1002", "HND-99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Handler HND-99 not found"}


def test_sign_off_by_handler_without_authority(client):
    approved(client, "CLM-1002", 1150)
    with closing(connect()) as db, db:
        db.execute(
            "UPDATE handlers SET data = json_set(data, '$.can_approve_over_limit',"
            " json('false')) WHERE handler_id = 'HND-03'"
        )
    response = sign_off(client, "CLM-1002", "HND-03")
    assert response.status_code == 403
    assert response.json() == {"detail": "Handler HND-03 cannot sign off"}


def test_list_claims_shows_decisions(client):
    approved(client, "CLM-1002", 1150)
    summary = client.get("/api/claims").json()[1]
    assert summary["status"] == "waiting_for_sign_off"
    assert summary["outcome"] == "approve"
    assert summary["payout"] == 1150
