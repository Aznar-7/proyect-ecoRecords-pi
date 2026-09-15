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
    expected_tmp_output = daemon._filter_cache_path(str(track)) + ".tmp"

    calls = []

    def _fake_run(cmd, **kwargs):
        calls.append(cmd)
        _touch(expected_tmp_output, b"filtered")  # simula que sox escribió el archivo de salida
        class _Result:
            returncode = 0
        return _Result()

    monkeypatch.setattr(daemon.subprocess, "run", _fake_run)

    result = daemon.get_filtered_track_path(str(track))

    assert os.path.exists(result)
    assert calls[0][0] == "sox"
    assert calls[0][1] == str(track)
    # Calidad de reencode explícita: sin esto, sox usa su propio default
    # (no documentado como alto), y recodificar un mp3 ya con pérdida por
    # segunda vez a baja calidad es lo que causaba el bajo/piano "raro" y
    # la voz apagada reportados — la pérdida de generación se nota más en
    # el contenido más sutil (voces suaves) y en transitorios (piano).
    assert "-C" in calls[0]
    assert daemon.MP3_ENCODE_QUALITY in calls[0]
    assert "bass" in calls[0]
    assert str(daemon.BASS_SHELF_GAIN_DB) in calls[0]
    assert str(daemon.BASS_SHELF_HZ) in calls[0]
    assert "norm" in calls[0]
    assert str(daemon.NORM_TARGET_DB) in calls[0]
    # El orden importa: normalizar tiene que medir el pico DESPUÉS del
    # shelf de graves, no antes — si no, el volumen final no refleja el
    # audio que realmente se va a reproducir.
    assert calls[0].index("bass") < calls[0].index("norm")


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


def test_get_filtered_track_path_leaves_no_corrupt_file_if_sox_dies_mid_write(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    track = tmp_path / "song.mp3"
    _touch(track)
    expected_tmp_output = daemon._filter_cache_path(str(track)) + ".tmp"

    def _fake_run(cmd, **kwargs):
        # sox alcanzó a escribir algo en el destino antes de morir a mitad
        # de camino (disco lleno, sin memoria, la señal que sea).
        _touch(expected_tmp_output, b"partial garbage")
        raise daemon.subprocess.CalledProcessError(1, cmd)
    monkeypatch.setattr(daemon.subprocess, "run", _fake_run)

    result = daemon.get_filtered_track_path(str(track))

    final_cache_path = daemon._filter_cache_path(str(track))
    assert result == str(track)
    assert not os.path.exists(final_cache_path)


def test_enforce_filter_cache_limit_does_nothing_under_limit(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(daemon, "FILTER_CACHE_MAX_BYTES", 1000)
    small_file = cache_dir / "a.mp3"
    _touch(small_file, b"x" * 100)

    daemon._enforce_filter_cache_limit()

    assert small_file.exists()


def test_enforce_filter_cache_limit_evicts_oldest_first_until_under_limit(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(cache_dir))
    monkeypatch.setattr(daemon, "FILTER_CACHE_MAX_BYTES", 150)

    old_file = cache_dir / "old.mp3"
    _touch(old_file, b"x" * 100)
    os.utime(old_file, (1000, 1000))  # el más viejo

    newer_file = cache_dir / "newer.mp3"
    _touch(newer_file, b"x" * 100)
    os.utime(newer_file, (2000, 2000))

    daemon._enforce_filter_cache_limit()

    assert not old_file.exists()
    assert newer_file.exists()


def test_enforce_filter_cache_limit_ignores_missing_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(daemon, "FILTER_CACHE_DIR", str(tmp_path / "no-existe"))
    monkeypatch.setattr(daemon, "FILTER_CACHE_MAX_BYTES", 1000)

    daemon._enforce_filter_cache_limit()  # no debe lanzar excepción
