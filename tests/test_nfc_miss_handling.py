import daemon


def test_handle_nfc_miss_increments_and_signals_removal_at_threshold(monkeypatch):
    monkeypatch.setattr(daemon, "is_paused", False)
    monkeypatch.setattr(daemon, "MISS_THRESHOLD", 3)

    count, should_remove = daemon.handle_nfc_miss(0)
    assert (count, should_remove) == (1, False)

    count, should_remove = daemon.handle_nfc_miss(count)
    assert (count, should_remove) == (2, False)

    count, should_remove = daemon.handle_nfc_miss(count)
    assert (count, should_remove) == (3, True)


def test_handle_nfc_miss_does_not_count_while_paused(monkeypatch):
    monkeypatch.setattr(daemon, "is_paused", True)
    monkeypatch.setattr(daemon, "MISS_THRESHOLD", 3)

    count, should_remove = daemon.handle_nfc_miss(2)

    assert count == 0
    assert should_remove is False
