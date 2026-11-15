from backend import agents


def test_get_instructions(client):
    instructions = client.get("/api/instructions").json()
    assert instructions["claim"].startswith("You are the UnderCover Agent.")
    assert instructions["queue"].startswith(
        "You are the UnderCover Agent, running the claims queue"
    )


def test_run_agent(client, monkeypatch):
    started = []
    monkeypatch.setattr(agents.claim, "run", lambda *args: started.append(args))
    response = client.post("/api/claims/CLM-1001/agent-runs")
    assert response.status_code == 202
    assert started == [("CLM-1001", response.json()["thread_id"])]


def test_run_agent_on_claim_not_waiting(client, monkeypatch):
    monkeypatch.setattr(agents.claim, "run", lambda *args: None)
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    response = client.post("/api/claims/CLM-1001/agent-runs")
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1001 is in progress"}


def test_run_queue_agent(client, monkeypatch):
    started = []
    monkeypatch.setattr(agents.queue, "work_queue", lambda *args: started.append(args))
    response = client.post("/api/queue/agent-runs", json={"cap": 5})
    assert response.status_code == 202
    assert started == [(response.json()["run_id"], 5)]


def test_only_this_module_imports_the_agent():
    importers = [
        path.name
        for path in agents.INSTRUCTIONS.parent.glob("*.py")
        if "from agent import" in path.read_text(encoding="utf-8")
    ]
    assert importers == ["agents.py"]
