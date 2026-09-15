import json

import daemon


def _base_config(albums=None):
    return {"albums": albums or {}, "volume": 70}


def test_recheck_current_uid_plays_album_if_now_known(tmp_path, monkeypatch, fake_popen):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_base_config({"UID1": "thriller"})))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(daemon, "STATS_PATH", str(tmp_path / "stats.json"))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
    monkeypatch.setattr(daemon, "get_filtered_track_path", lambda path: path)
    monkeypatch.setattr(daemon, "get_tracks", lambda album: ["01 - A.mp3"])
    monkeypatch.setattr(daemon, "start_motor", lambda: None)
    daemon.current_uid = "UID1"

    daemon.recheck_current_uid()

    assert daemon.current_album == "thriller"
    assert len(fake_popen.instances) == 1


def test_recheck_current_uid_does_nothing_when_still_unknown(tmp_path, monkeypatch, fake_popen):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_base_config()))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    daemon.current_uid = "UID_UNKNOWN"

    daemon.recheck_current_uid()

    assert len(fake_popen.instances) == 0


def test_recheck_current_uid_does_nothing_when_no_disc_present(fake_popen):
    daemon.current_uid = None

    daemon.recheck_current_uid()

    assert len(fake_popen.instances) == 0
