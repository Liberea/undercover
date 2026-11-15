from agent import model


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    default = model.model()
    assert default.model_name == "deepseek/deepseek-v4.1-flash"
    assert default.reasoning_effort == "low"
    assert default.request_timeout == model.TIMEOUT_SECONDS
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    chosen = model.model()
    assert chosen.model_name == "openrouter/free"
    assert chosen.reasoning_effort is None
