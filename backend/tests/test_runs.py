from agent import main as agent

STEP = {"thread_id": "t-1", "kind": "tool_call", "text": "get_claim"}


def test_add_and_list_steps(client):
    step = client.post("/api/claims/CLM-1001/steps", json=STEP).json()
    assert step == STEP | {"step_id": 1, "created_at": step["created_at"]}
    assert client.get("/api/claims/CLM-1001/steps").json() == [step]


def test_steps_of_unknown_claim(client):
    assert client.post("/api/claims/CLM-9999/steps", json=STEP).status_code == 404
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_unknown_step_kind(client):
    step = STEP | {"kind": "thought"}
    assert client.post("/api/claims/CLM-1001/steps", json=step).status_code == 422


def test_run_agent(client, monkeypatch):
    started = []
    monkeypatch.setattr(agent, "run", lambda *args: started.append(args))
    response = client.post("/api/claims/CLM-1001/agent-runs")
    assert response.status_code == 202
    assert started == [("CLM-1001", response.json()["thread_id"])]


def test_run_agent_on_claim_not_waiting(client, monkeypatch):
    monkeypatch.setattr(agent, "run", lambda *args: None)
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t-1"})
    response = client.post("/api/claims/CLM-1001/agent-runs")
    assert response.status_code == 409
    assert response.json() == {"detail": "Claim CLM-1001 is in progress"}


def test_get_instructions(client):
    text = client.get("/api/instructions").json()["text"]
    assert text.startswith("You are the UnderCover Agent.")
