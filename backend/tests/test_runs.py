TODOS = [
    {"content": "Work CLM-1001", "status": "done"},
    {"content": "Work CLM-1002", "status": "left_for_handler"},
    {"content": "Write the summary", "status": "in_progress"},
]


def create(client, run_id, cap=5):
    return client.post("/api/runs", json={"run_id": run_id, "cap": cap})


def test_create_run(client):
    response = create(client, "r-1")
    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "running"
    assert run["cap"] == 5
    assert run["todos"] == []
    assert run["summary"] is None
    assert run["finished_at"] is None


def test_a_cap_must_be_at_least_one(client):
    assert create(client, "r-1", cap=0).status_code == 422


def test_write_todos_replaces_the_list(client):
    create(client, "r-1")
    client.put("/api/runs/r-1/todos", json={"todos": TODOS})
    run = client.put("/api/runs/r-1/todos", json={"todos": TODOS[:1]}).json()
    assert run["todos"] == TODOS[:1]


def test_unknown_todo_status(client):
    create(client, "r-1")
    todos = [{"content": "Work CLM-1001", "status": "pending"}]
    assert client.put("/api/runs/r-1/todos", json={"todos": todos}).status_code == 422


def test_todos_of_unknown_run(client):
    response = client.put("/api/runs/r-9/todos", json={"todos": TODOS})
    assert response.status_code == 404
    assert response.json() == {"detail": "Run r-9 not found"}


def test_finish_run(client):
    create(client, "r-1")
    run = client.post("/api/runs/r-1/finish", json={"summary": "All done."}).json()
    assert run["status"] == "finished"
    assert run["summary"] == "All done."
    assert run["finished_at"] is not None
    again = client.post("/api/runs/r-1/finish", json={"summary": "Again."})
    assert again.status_code == 409


def test_latest_run(client):
    response = client.get("/api/runs/latest")
    assert response.status_code == 200
    assert response.json() is None
    create(client, "r-1")
    create(client, "r-2", cap=2)
    assert client.get("/api/runs/latest").json()["run_id"] == "r-2"
