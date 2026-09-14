import json

import app as app_module


def test_reset_now_playing_clears_playback_but_keeps_other_keys(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "albums": {"UID1": "album-x"},
        "volume": 55,
        "command": None,
        "now_playing": {
            "album": "album-x", "track": 3, "track_name": "Song",
            "total": 8, "playing": True,
        },
    }))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))

    app_module.reset_now_playing()

    saved = json.loads(config_path.read_text())
    assert saved["now_playing"]["playing"] is False
    assert saved["now_playing"]["album"] is None
    assert saved["albums"] == {"UID1": "album-x"}
    assert saved["volume"] == 55
