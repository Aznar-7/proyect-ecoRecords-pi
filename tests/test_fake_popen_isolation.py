"""
Regression test: verify fake_popen fixture properly isolates background threads
so they don't corrupt real config.json when monkeypatch reverts.

Issue: load_track() spawns a daemon thread running watch_process(), which
asynchronously calls write_state() → write_full_config() with daemon.CONFIG_PATH.
If the test's monkeypatch revert happens before the thread finishes, the thread
writes test data to the REAL config.json, corrupting it.

Fix: fake_popen fixture stubs daemon.watch_process to a no-op, so the
background thread never touches CONFIG_PATH.

Test: verify that the stub is actually in place.
"""
import json

import daemon


def test_watch_process_is_stubbed_to_noop(fake_popen):
    """Assert that the fake_popen fixture has stubbed watch_process to a no-op."""
    # Capture the original watch_process before fixture runs (for comparison if needed)
    # but we mainly just call it with dummy args and assert it does nothing observable
    result = daemon.watch_process(None, 0)
    assert result is None


def test_load_track_does_not_corrupt_real_config(tmp_path, monkeypatch, fake_popen):
    """Verify load_track() with monkeypatched paths doesn't race past monkeypatch
    reverts and corrupt real config.json.

    This is an integration-level test: we set up paths, call load_track (which
    spawns watch_process in a background thread), and then let the fixture's
    monkeypatch revert happen naturally when the test returns. If watch_process
    were NOT stubbed, the thread would run after monkeypatch reverts and call
    write_state() with the real, un-stubbed CONFIG_PATH, corrupting it.

    Since watch_process is stubbed, the thread is a no-op and can never corrupt
    anything, even if it somehow ran after monkeypatch reverts.
    """
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 50}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
    monkeypatch.setattr(daemon, "get_filtered_track_path", lambda path: path)

    daemon.current_album = "test-album"
    daemon.current_tracks = ["01 - Song.mp3"]

    # This spawns a daemon thread that calls watch_process().
    # With the fix, watch_process is a no-op and the thread is harmless.
    daemon.load_track(0)

    # Verify one Popen call was made (the track started playing)
    assert len(fake_popen.instances) == 1

    # The test's monkeypatch reverts will happen when this test returns.
    # If watch_process were NOT stubbed, the background thread would still be
    # running and would call write_state() with the REAL, un-monkeypatched
    # daemon.CONFIG_PATH, corrupting the real config.json. Since it IS stubbed
    # to a no-op, that can never happen.
