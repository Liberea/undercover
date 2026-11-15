from agent import harness
from agent.tests.stubs import reply


def test_retry_twice_then_raise():
    retry = harness.retry()
    assert retry.max_retries == 2
    assert retry.on_failure == "error"


def test_middleware_updates_hold_no_messages():
    updates = [
        {"ModelCallLimitMiddleware.before_model": None},
        {"model": {"messages": [reply("Done.")]}},
        {"ModelCallLimitMiddleware.after_model": {"run_model_call_count": 1}},
    ]
    assert [m.text for m in harness.messages(updates)] == ["Done."]
