import json

from app.services.events import append_event
from app.services.projects import create_project


def test_stream_events_replays_backlog_after_last_event_id(api_client, db_session, monkeypatch):
    from app.api import events as events_module

    # Keep this test fast and its background polling thread short-lived
    # regardless of whether the sync TestClient's transport ever reports the
    # request as disconnected once we stop reading it.
    monkeypatch.setattr(events_module, "_POLL_INTERVAL_SECONDS", 0.02)
    monkeypatch.setattr(events_module, "_MAX_IDLE_POLLS", 5)

    project = create_project(db_session, name="SSE Testi")
    e1 = append_event(db_session, project_id=project.id, type="test.one", payload={"n": 1})
    e2 = append_event(db_session, project_id=project.id, type="test.two", payload={"n": 2})

    collected = ""
    with api_client.stream(
        "GET", "/api/v1/events", headers={"Last-Event-ID": str(e1.sequence - 1)}
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        for chunk in response.iter_text():
            collected += chunk
            if collected.count("\n\n") >= 2:
                break

    blocks = [b for b in collected.split("\n\n") if b.strip()]
    assert len(blocks) >= 2

    def _payload(block: str) -> dict:
        data_line = next(line for line in block.splitlines() if line.startswith("data: "))
        return json.loads(data_line[len("data: ") :])

    first = _payload(blocks[0])
    second = _payload(blocks[1])
    assert first["type"] == "test.one"
    assert first["sequence"] == e1.sequence
    assert second["type"] == "test.two"
    assert second["sequence"] == e2.sequence
