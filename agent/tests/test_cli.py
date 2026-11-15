from agent import __main__ as cli


def test_works_one_named_claim(monkeypatch, capsys):
    monkeypatch.setattr(cli, "run", lambda claim_id, _: f"{claim_id}: declined")
    cli.main(["CLM-1001"])
    assert capsys.readouterr().out == "CLM-1001: declined\n"


def test_works_the_queue_up_to_the_cap(monkeypatch, capsys):
    caps = []
    monkeypatch.setattr(cli, "work_queue", lambda _, cap: caps.append(cap) or "Done.")
    cli.main(["--cap", "5"])
    assert caps == [5]
    assert capsys.readouterr().out == "Done.\n"


def test_works_the_whole_queue(client, monkeypatch):
    caps = []
    monkeypatch.setattr(cli, "work_queue", lambda _, cap: caps.append(cap) or "")
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    cli.main([])
    assert caps == [24]


def test_nothing_waiting(monkeypatch, capsys):
    monkeypatch.setattr(cli, "waiting_claims", list)
    cli.main([])
    assert capsys.readouterr().out == "No claims are waiting.\n"
