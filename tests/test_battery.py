import json

import daemon


class FakeIna:
    def __init__(self, voltage, current):
        self._voltage = voltage
        self._current = current

    def voltage(self):
        return self._voltage

    def current(self):
        return self._current


def test_battery_percent_full():
    assert daemon.battery_percent(4.2) == 100


def test_battery_percent_empty():
    assert daemon.battery_percent(3.0) == 0


def test_battery_percent_clamps_below_range():
    assert daemon.battery_percent(2.5) == 0


def test_battery_percent_clamps_above_range():
    assert daemon.battery_percent(4.5) == 100


def test_battery_percent_midpoint():
    assert daemon.battery_percent(3.6) == 50


def test_read_battery_discharging():
    result = daemon.read_battery(FakeIna(3.6, -120))
    assert result == {"percent": 50, "charging": False}


def test_read_battery_charging():
    result = daemon.read_battery(FakeIna(4.0, 300))
    assert result["charging"] is True


def test_update_battery_config_preserves_existing_keys(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"albums": {"UID1": "album-x"}, "volume": 80}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))

    daemon.update_battery_config(FakeIna(3.9, -50))

    saved = json.loads(config_path.read_text())
    assert saved["albums"] == {"UID1": "album-x"}
    assert saved["volume"] == 80
    assert saved["battery"] == {"percent": round((3.9 - 3.0) / 1.2 * 100), "charging": False}
