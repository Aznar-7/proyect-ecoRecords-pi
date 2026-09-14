import json

import daemon


def _write_config(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def test_volume_factor_full(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_config(config_path, {"volume": 100})
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    assert daemon.get_volume_scale_factor() == 32768


def test_volume_factor_default_when_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_config(config_path, {})
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    assert daemon.get_volume_scale_factor() == int(70 / 100 * 32768)


def test_volume_factor_zero(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_config(config_path, {"volume": 0})
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    assert daemon.get_volume_scale_factor() == 0


def test_build_command_basic():
    cmd = daemon.build_mpg123_command("/albums/x/01.mp3", 32768)
    assert cmd == ["mpg123", "-q", "-f", "32768", "--audiodevice", "plughw:0,0", "/albums/x/01.mp3"]


def test_build_command_with_resume():
    cmd = daemon.build_mpg123_command("/albums/x/01.mp3", 16384, skip_frames=140)
    assert cmd == ["mpg123", "-q", "-f", "16384", "-k", "140", "--audiodevice", "plughw:0,0", "/albums/x/01.mp3"]
