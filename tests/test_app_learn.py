import json

import app as app_module


def test_learn_disc_sets_recheck_command_so_daemon_plays_it_immediately(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "albums": {}, "pending_uid": "UID1", "command": None, "volume": 70,
    }))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))
    client = app_module.app.test_client()

    res = client.post("/api/learn", json={"uid": "UID1", "album": "thriller"})

    assert res.get_json()["ok"] is True
    saved = json.loads(config_path.read_text())
    assert saved["albums"]["UID1"] == "thriller"
    assert saved["command"] == "recheck_uid"
    assert "pending_uid" not in saved
