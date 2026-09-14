import json

import daemon


def test_increment_album_stat_creates_file(tmp_path, monkeypatch):
    stats_path = tmp_path / "stats.json"
    monkeypatch.setattr(daemon, "STATS_PATH", str(stats_path))

    daemon.increment_album_stat("thriller")

    assert json.loads(stats_path.read_text()) == {"thriller": 1}


def test_increment_album_stat_increments_existing(tmp_path, monkeypatch):
    stats_path = tmp_path / "stats.json"
    stats_path.write_text(json.dumps({"thriller": 3, "02-09": 1}))
    monkeypatch.setattr(daemon, "STATS_PATH", str(stats_path))

    daemon.increment_album_stat("thriller")

    assert json.loads(stats_path.read_text()) == {"thriller": 4, "02-09": 1}


def test_read_stats_handles_corrupted_json(tmp_path, monkeypatch, capsys):
    stats_path = tmp_path / "stats.json"
    stats_path.write_text("{invalid json content")
    monkeypatch.setattr(daemon, "STATS_PATH", str(stats_path))

    result = daemon.read_stats()

    assert result == {}
    captured = capsys.readouterr()
    assert "[ECO] stats.json corrupto, arranco de cero:" in captured.out


def test_play_album_counts_once_even_with_multiple_tracks(tmp_path, monkeypatch, fake_popen):
    stats_path = tmp_path / "stats.json"
    history_path = tmp_path / "history.json"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 70}))
    monkeypatch.setattr(daemon, "STATS_PATH", str(stats_path))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
    monkeypatch.setattr(daemon, "get_tracks", lambda album: ["01 - A.mp3", "02 - B.mp3"])
    monkeypatch.setattr(daemon, "start_motor", lambda: None)
    monkeypatch.setattr(daemon, "log_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(daemon, "get_filtered_track_path", lambda path: path)

    daemon.play_album("thriller")
    daemon.next_track()

    assert json.loads(stats_path.read_text()) == {"thriller": 1}
