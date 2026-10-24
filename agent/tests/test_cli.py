from agent import __main__ as cli


def test_runs_the_claims_given(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run", lambda claim_id, _: f"Decided {claim_id}.")
    cli.main(["CLM-1001"])
    assert capsys.readouterr().out == "CLM-1001: Decided CLM-1001.\n"


def test_works_through_the_waiting_claims(client, monkeypatch):
    ran = []
    monkeypatch.setattr(cli, "run", lambda claim_id, _: ran.append(claim_id) or "")
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    cli.main([])
    assert len(ran) == 24
    assert "CLM-1001" not in ran
