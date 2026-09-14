import json

import daemon


def test_log_history_appends_entry(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon.time, "time", lambda: 1700000000.0)

    daemon.log_history("thriller", "Beat It")

    saved = json.loads(history_path.read_text())
    assert saved == [{"album": "thriller", "track_name": "Beat It", "timestamp": 1700000000.0}]


def test_log_history_appends_to_existing_file(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps([{"album": "a", "track_name": "t1", "timestamp": 1.0}]))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon.time, "time", lambda: 2.0)

    daemon.log_history("b", "t2")

    saved = json.loads(history_path.read_text())
    assert saved == [
        {"album": "a", "track_name": "t1", "timestamp": 1.0},
        {"album": "b", "track_name": "t2", "timestamp": 2.0},
    ]


def test_log_history_caps_at_50_entries(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    existing = [{"album": "a", "track_name": f"t{i}", "timestamp": float(i)} for i in range(50)]
    history_path.write_text(json.dumps(existing))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon.time, "time", lambda: 999.0)

    daemon.log_history("a", "newest")

    saved = json.loads(history_path.read_text())
    assert len(saved) == 50
    assert saved[-1] == {"album": "a", "track_name": "newest", "timestamp": 999.0}
    assert saved[0]["track_name"] == "t1"  # se descartó t0, la más vieja
