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
