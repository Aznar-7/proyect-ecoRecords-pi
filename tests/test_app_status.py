import json

import app as app_module


def _base_config(extra=None):
    config = {
        "albums": {}, "volume": 70, "command": None,
        "now_playing": {"album": None, "track": 0, "track_name": None, "total": 0, "playing": False},
    }
    if extra:
        config.update(extra)
    return config


def test_status_includes_battery_field(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_base_config({"battery": {"percent": 42, "charging": True}})))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))
    client = app_module.app.test_client()

    res = client.get("/api/status")

    assert res.get_json()["battery"] == {"percent": 42, "charging": True}


def test_status_defaults_battery_when_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_base_config()))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))
    client = app_module.app.test_client()

    res = client.get("/api/status")

    assert res.get_json()["battery"] == {"percent": None, "charging": False}
