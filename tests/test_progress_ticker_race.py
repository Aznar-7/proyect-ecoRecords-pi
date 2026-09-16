import json
import threading
import time

import daemon


def test_progress_tick_writes_elapsed_when_playing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 70}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))

    daemon.current_album = "thriller"
    daemon.current_tracks = ["01 - Beat It.mp3"]
    daemon.current_index = 0
    daemon.current_duration = 180
    daemon.is_paused = False
    daemon.accumulated_elapsed = 10
    daemon.track_start_time = time.time() - 5  # 5s reproduciendo desde que arrancó

    last_written = daemon._progress_tick(-1)

    assert last_written == 15
    saved = json.loads(config_path.read_text())
    assert saved["now_playing"]["elapsed"] == 15
    assert saved["now_playing"]["playing"] is True


def test_progress_tick_does_nothing_while_paused(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 70}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))

    daemon.current_album = "thriller"
    daemon.current_tracks = ["01 - Beat It.mp3"]
    daemon.current_index = 0
    daemon.is_paused = True

    result = daemon._progress_tick(-1)

    assert result == -1
    # No debe haber tocado el archivo — nada que reportar mientras está pausado.
    saved = json.loads(config_path.read_text())
    assert "now_playing" not in saved


def test_progress_tick_skips_write_when_elapsed_unchanged(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 70}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))

    daemon.current_album = "thriller"
    daemon.current_tracks = ["01 - Beat It.mp3"]
    daemon.current_index = 0
    daemon.current_duration = 180
    daemon.is_paused = False
    daemon.accumulated_elapsed = 0
    daemon.track_start_time = time.time()

    write_calls = []
    monkeypatch.setattr(daemon, "write_state", lambda *a, **k: write_calls.append(a))

    result = daemon._progress_tick(0)  # ya se había escrito "0" antes

    assert result == 0
    assert write_calls == []  # no vuelve a escribir el mismo valor


def test_progress_tick_serializes_with_playback_state_lock(tmp_path, monkeypatch):
    # Prueba directa del mecanismo del fix: _progress_tick tiene que
    # esperar el mismo lock que usan _pause_now/_resume_now antes de leer
    # el estado compartido, para no ver una foto a medio actualizar.
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 70}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))

    daemon.current_album = "thriller"
    daemon.current_tracks = ["01 - Beat It.mp3"]
    daemon.current_index = 0
    daemon.current_duration = 180
    daemon.is_paused = False
    daemon.accumulated_elapsed = 0
    daemon.track_start_time = time.time()

    results = []

    daemon.lock.acquire()
    try:
        t = threading.Thread(target=lambda: results.append(daemon._progress_tick(-1)))
        t.start()
        t.join(timeout=0.3)
        # Con el lock tomado del lado del test, _progress_tick todavía no
        # debería haber podido terminar.
        assert t.is_alive(), "_progress_tick no esperó el lock compartido"
    finally:
        daemon.lock.release()

    t.join(timeout=1)
    assert not t.is_alive()
    assert results
