import json

import app as app_module


def test_stats_route_returns_top_album(tmp_path, monkeypatch):
    stats_path = tmp_path / "stats.json"
    stats_path.write_text(json.dumps({"thriller": 5, "02-09": 2}))
    monkeypatch.setattr(app_module, "STATS_PATH", str(stats_path))
    client = app_module.app.test_client()

    res = client.get("/api/stats")

    assert res.get_json() == {"albums": {"thriller": 5, "02-09": 2}, "top_album": "thriller"}


def test_stats_route_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "STATS_PATH", str(tmp_path / "missing.json"))
    client = app_module.app.test_client()

    res = client.get("/api/stats")

    assert res.get_json() == {"albums": {}, "top_album": None}
