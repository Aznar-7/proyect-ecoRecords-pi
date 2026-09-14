import json

import app as app_module


def test_history_route_returns_most_recent_first(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps([
        {"album": "a", "track_name": "t1", "timestamp": 1.0},
        {"album": "b", "track_name": "t2", "timestamp": 2.0},
    ]))
    monkeypatch.setattr(app_module, "HISTORY_PATH", str(history_path))
    client = app_module.app.test_client()

    res = client.get("/api/history")

    assert res.get_json() == [
        {"album": "b", "track_name": "t2", "timestamp": 2.0},
        {"album": "a", "track_name": "t1", "timestamp": 1.0},
    ]


def test_history_route_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "HISTORY_PATH", str(tmp_path / "missing.json"))
    client = app_module.app.test_client()

    res = client.get("/api/history")

    assert res.get_json() == []
