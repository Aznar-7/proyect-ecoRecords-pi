import os

import daemon


def _touch(path, content=b"fake mp3 bytes"):
    with open(path, "wb") as f:
        f.write(content)


def test_filter_cache_path_is_stable_for_same_input(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    track = tmp_path / "song.mp3"
    _touch(track)

    path_a = daemon._filter_cache_path(str(track))
    path_b = daemon._filter_cache_path(str(track))

    assert path_a == path_b
    assert path_a.endswith(".mp3")
    assert os.path.dirname(path_a) == str(cache_dir)


def test_filter_cache_path_differs_for_different_tracks(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    track_a = tmp_path / "a.mp3"
    track_b = tmp_path / "b.mp3"
    _touch(track_a)
    _touch(track_b)

    assert daemon._filter_cache_path(str(track_a)) != daemon._filter_cache_path(str(track_b))


def test_get_filtered_track_path_returns_cache_hit_without_calling_sox(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    track = tmp_path / "song.mp3"
    _touch(track)
    cache_path = daemon._filter_cache_path(str(track))
    os.makedirs(cache_dir, exist_ok=True)
    _touch(cache_path, b"already filtered")

    def _fail_if_called(*a, **k):
        raise AssertionError("sox no debería correr en un cache hit")
    monkeypatch.setattr(daemon.subprocess, "run", _fail_if_called)

    result = daemon.get_filtered_track_path(str(track))

    assert result == cache_path


def test_get_filtered_track_path_runs_sox_on_cache_miss(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    track = tmp_path / "song.mp3"
    _touch(track)

    calls = []

    def _fake_run(cmd, **kwargs):
        calls.append(cmd)
        _touch(cmd[2], b"filtered")  # simula que sox escribió el archivo de salida
        class _Result:
            returncode = 0
        return _Result()

    monkeypatch.setattr(daemon.subprocess, "run", _fake_run)

    result = daemon.get_filtered_track_path(str(track))

    assert os.path.exists(result)
    assert calls[0][0] == "sox"
    assert calls[0][1] == str(track)
    assert "bass" in calls[0]
    assert str(daemon.BASS_SHELF_GAIN_DB) in calls[0]
    assert str(daemon.BASS_SHELF_HZ) in calls[0]


def test_get_filtered_track_path_falls_back_to_original_on_sox_failure(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    track = tmp_path / "song.mp3"
    _touch(track)

    def _fake_run(cmd, **kwargs):
        raise daemon.subprocess.CalledProcessError(1, cmd)
    monkeypatch.setattr(daemon.subprocess, "run", _fake_run)

    result = daemon.get_filtered_track_path(str(track))

    assert result == str(track)
