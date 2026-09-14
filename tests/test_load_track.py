import json

import daemon


def test_load_track_applies_current_volume_factor(tmp_path, monkeypatch, fake_popen):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 50}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
    monkeypatch.setattr(daemon, "get_filtered_track_path", lambda path: path)

    daemon.current_album = "test-album"
    daemon.current_tracks = ["01 - Song.mp3"]

    daemon.load_track(0)

    assert len(fake_popen.instances) == 1
    cmd = fake_popen.instances[0].args
    expected_factor = str(int(50 / 100 * 32768))
    assert cmd[:4] == ["mpg123", "-q", "-f", expected_factor]
