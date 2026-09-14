import daemon


def test_daemon_module_imports_without_real_hardware():
    assert daemon.BASE_DIR
    assert callable(daemon.load_track)
