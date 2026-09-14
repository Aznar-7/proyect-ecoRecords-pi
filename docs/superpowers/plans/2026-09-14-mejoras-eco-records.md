# Mejoras Eco Records (volumen, filtro de graves, batería, historial, estadísticas, UI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add software volume control, a bass high-pass filter, a battery indicator (INA219), playback history, basic usage stats, and a polished restart modal to the Eco Records NFC record player, without breaking the existing daemon/Flask/config.json contract.

**Architecture:** `daemon.py` keeps owning all hardware/playback state and writes to `config.json` (and two new flat files, `history.json` and `stats.json`); `app.py` stays a thin reader that exposes new fields/routes; the frontend (`templates/index.html`, `static/js/app.js`, `static/css/style.css`) polls the existing `/api/status` plus two new read-only routes. No new processes, no new heavy dependencies — `sox` (already tiny, apt-installable) is the only new system package, used for the bass filter.

**Tech Stack:** Python 3 (Flask, threading, subprocess), `pi-ina219`, `sox` (system package), vanilla JS/CSS/HTML, `pytest` (new, dev-only) for the pure-logic parts that don't need real hardware.

**Spec:** [docs/superpowers/specs/2026-09-14-mejoras-eco-records.md](../specs/2026-09-14-mejoras-eco-records.md)

## Global Constraints

- Raspberry Pi Zero 2W, 512MB RAM — no new heavy dependencies; `sox` is the only new system package.
- Any new polling loop (battery, etc.) must be a `threading.Thread(..., daemon=True)` with its own `time.sleep`, never blocking the main NFC loop.
- Every `config.json` write must preserve existing keys: `albums`, `now_playing`, `command`, `volume`, `lights`.
- Follow existing style: `threading.Lock()` for shared state, explicit `try/except` in main loops, `[ECO]` log prefix, short single-responsibility functions, no new classes when a function suffices, comments only where something isn't obvious.
- Test each feature in isolation before wiring it to the others.
- `sudo`/`reboot`/real GPIO/I2C/mpg123/sox execution cannot be verified from this dev machine — those steps are marked as **manual verification on the Pi** with an exact command to run, not skipped.

---

## File Structure

| File | Responsibility |
|---|---|
| `requirements-dev.txt` (new) | `pytest`, dev-only, not needed on the Pi in production |
| `tests/conftest.py` (new) | Stubs `board`, `busio`, `RPi.GPIO`, `adafruit_pn532.i2c`, `ina219` in `sys.modules` so `daemon.py` imports on a machine without Raspberry Pi hardware; shared `fake_popen` fixture; autouse fixture that resets `daemon`'s shared globals after every test |
| `tests/test_daemon_imports.py` (new) | Smoke test: `daemon.py` imports cleanly under the stubs |
| `tests/test_app_reset_now_playing.py` (new) | Covers `app.reset_now_playing()` in isolation |
| `tests/test_volume.py` (new) | `get_volume_scale_factor`, `build_mpg123_command` |
| `tests/test_load_track.py` (new) | Integration-ish test: `load_track` builds the right `mpg123` command (updated in later tasks as `load_track` grows) |
| `tests/test_battery.py` (new) | `battery_percent`, `read_battery`, `update_battery_config` |
| `tests/test_app_status.py` (new) | `/api/status` battery field |
| `tests/test_history.py` (new) | `log_history` trimming/shape |
| `tests/test_app_history.py` (new) | `/api/history` route |
| `tests/test_stats.py` (new) | `increment_album_stat` |
| `tests/test_app_stats.py` (new) | `/api/stats` route |
| `tests/test_audio_filter.py` (new) | `get_filtered_track_path` cache hit/miss/fallback |
| `daemon.py` (modify) | All new pure logic + threads: volume factor, battery ticker, history logging, stats counting, bass filter caching; wiring into `load_track` / `_resume_now` / `play_album` |
| `app.py` (modify) | Import-safety fix (`reset_now_playing()` moved under `__main__` guard), `/api/status` battery field, new `/api/history`, new `/api/stats` |
| `templates/index.html` (modify) | Battery indicator markup in the home header; history/stats section in the Discos view; restructured settings-modal restart button (danger zone + spinner) |
| `static/js/app.js` (modify) | Render battery, fetch+render history/stats, restart button loading/disabled state |
| `static/css/style.css` (modify) | Styles for the above, matching the existing warm brown/amber palette and serif/sans type |
| `.gitignore` (modify) | Ignore `.filter_cache/`, `history.json`, `stats.json` (generated runtime data/cache, unlike the intentionally-tracked example `config.json`) |
| `README.md` (modify) | Add `sox` to the system-package install line, add `pytest` note for running tests on a dev machine |

---

### Task 1: Test infrastructure + app.py import-safety fix

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Create: `tests/test_daemon_imports.py`
- Create: `tests/test_app_reset_now_playing.py`
- Modify: `app.py:36` (and the bottom `if __name__ == "__main__":` block)

**Interfaces:**
- Produces: `tests/conftest.py` fixtures `fake_popen` (records `subprocess.Popen` calls made through `daemon.subprocess.Popen`) and an autouse `reset_daemon_state` fixture that resets `daemon.current_album`, `daemon.current_tracks`, `daemon.current_index`, `daemon.is_paused`, `daemon.track_started` after each test and calls `daemon.stop_motor()` / `daemon.kill_current_process()`.
- Consumes: nothing yet (foundational task).

- [ ] **Step 1: Fix the import-time side effect in `app.py`**

`app.py` currently calls `reset_now_playing()` unconditionally at module import time (line 36), which would overwrite the **real** `config.json` (including real NFC UID→album mappings) the moment any test — or any tool — imports `app.py`. Move the call so it only runs when `app.py` is executed directly, matching how it's already run in production (`python3 app.py` via systemd).

Find:
```python
reset_now_playing()

@app.after_request
```

Replace with:
```python
@app.after_request
```

Find:
```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

Replace with:
```python
if __name__ == "__main__":
    reset_now_playing()
    app.run(host="0.0.0.0", port=5000)
```

- [ ] **Step 2: Add the dev test dependency**

Create `requirements-dev.txt`:
```
pytest
```

- [ ] **Step 3: Create the hardware stubs and shared fixtures**

Create `tests/conftest.py`:
```python
"""
Stubs de hardware para poder importar daemon.py y correr los tests en una
máquina sin Raspberry Pi. daemon.py hace `import board`, `import busio`,
`import RPi.GPIO`, `from adafruit_pn532.i2c import PN532_I2C` a nivel de
módulo, así que estos stubs tienen que existir en sys.modules ANTES de que
cualquier test haga `import daemon`. conftest.py se carga antes que los
tests, así que este es el lugar correcto.
"""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _stub_module(name, **attrs):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    sys.modules[name] = mod
    return mod


class _FakeGPIO:
    BCM = "BCM"
    OUT = "OUT"

    @staticmethod
    def setmode(mode):
        pass

    @staticmethod
    def setup(pin, mode):
        pass

    @staticmethod
    def output(pin, val):
        pass

    @staticmethod
    def cleanup():
        pass


_stub_module("board", SCL="SCL", SDA="SDA")
_stub_module("busio", I2C=lambda *a, **k: None)

_rpi_gpio = _stub_module(
    "RPi.GPIO",
    BCM=_FakeGPIO.BCM, OUT=_FakeGPIO.OUT,
    setmode=_FakeGPIO.setmode, setup=_FakeGPIO.setup,
    output=_FakeGPIO.output, cleanup=_FakeGPIO.cleanup,
)
_stub_module("RPi", GPIO=_rpi_gpio)


class _FakePN532:
    def __init__(self, *a, **k):
        pass


_adafruit_pn532 = _stub_module("adafruit_pn532")
_adafruit_pn532_i2c = _stub_module("adafruit_pn532.i2c", PN532_I2C=_FakePN532)
_adafruit_pn532.i2c = _adafruit_pn532_i2c


class _FakeINA219:
    def __init__(self, *a, **k):
        pass

    def configure(self):
        pass

    def voltage(self):
        return 3.7

    def current(self):
        return -100


_stub_module("ina219", INA219=_FakeINA219)

import daemon  # noqa: E402  (import diferido: necesita los stubs de arriba)


class FakePopen:
    """Reemplaza subprocess.Popen en los tests: no ejecuta nada de verdad,
    solo registra con qué argumentos se lo llamó."""

    instances = []

    def __init__(self, args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.returncode = 0
        FakePopen.instances.append(self)

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def terminate(self):
        pass

    def kill(self):
        pass


@pytest.fixture
def fake_popen(monkeypatch):
    FakePopen.instances = []
    monkeypatch.setattr(daemon.subprocess, "Popen", FakePopen)
    return FakePopen


@pytest.fixture(autouse=True)
def reset_daemon_state():
    yield
    daemon.stop_motor()
    daemon.kill_current_process()
    daemon.current_album = None
    daemon.current_tracks = []
    daemon.current_index = 0
    daemon.is_paused = True
    daemon.track_started = False
```

- [ ] **Step 4: Write the smoke test**

Create `tests/test_daemon_imports.py`:
```python
import daemon


def test_daemon_module_imports_without_real_hardware():
    assert daemon.BASE_DIR
    assert callable(daemon.load_track)
```

- [ ] **Step 5: Run it to verify it passes**

Run: `pytest tests/test_daemon_imports.py -v`
Expected: PASS (the stubs let `daemon.py`'s hardware imports resolve).

- [ ] **Step 6: Write the `reset_now_playing` test**

Create `tests/test_app_reset_now_playing.py`:
```python
import json

import app as app_module


def test_reset_now_playing_clears_playback_but_keeps_other_keys(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "albums": {"UID1": "album-x"},
        "volume": 55,
        "command": None,
        "now_playing": {
            "album": "album-x", "track": 3, "track_name": "Song",
            "total": 8, "playing": True,
        },
    }))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))

    app_module.reset_now_playing()

    saved = json.loads(config_path.read_text())
    assert saved["now_playing"]["playing"] is False
    assert saved["now_playing"]["album"] is None
    assert saved["albums"] == {"UID1": "album-x"}
    assert saved["volume"] == 55
```

- [ ] **Step 7: Run the full suite so far**

Run: `pytest -v`
Expected: 2 passed (this step must run *after* Step 1's fix — otherwise importing `app` in Step 6's test would have clobbered the real `config.json` the first time `app` was imported in the test session).

- [ ] **Step 8: Commit**

```bash
git add requirements-dev.txt tests/conftest.py tests/test_daemon_imports.py tests/test_app_reset_now_playing.py app.py
git commit -m "test: add pytest infra with hardware stubs, fix app.py import side effect"
```

---

### Task 2: Software volume control

**Files:**
- Modify: `daemon.py` (add `get_volume_scale_factor`, `build_mpg123_command`; wire into `load_track` and `_resume_now`)
- Test: `tests/test_volume.py`
- Test: `tests/test_load_track.py`

**Interfaces:**
- Consumes: `read_config()` (existing), `tests/conftest.py`'s `fake_popen` fixture (Task 1).
- Produces: `daemon.get_volume_scale_factor() -> int`, `daemon.build_mpg123_command(track_path: str, volume_factor: int, skip_frames: int | None = None) -> list[str]`. Later tasks (Task 9) will extend `build_mpg123_command`'s caller, not its signature.

- [ ] **Step 1: Write the failing tests for the pure functions**

Create `tests/test_volume.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_volume.py -v`
Expected: FAIL with `AttributeError: module 'daemon' has no attribute 'get_volume_scale_factor'`.

- [ ] **Step 3: Implement the pure functions in `daemon.py`**

Add near the `# ── Config ───` section (right after `clear_command()`):
```python
def get_volume_scale_factor():
    """Convierte el volumen guardado en config.json (0-100) al factor de
    escala que espera mpg123 (-f), donde 32768 = 100%."""
    config = read_config()
    volume_pct = config.get("volume", 70)
    return int((volume_pct / 100) * 32768)
```

Add near the `# ── Control de audio (proceso limpio por pista) ──` section (right before `def load_track`):
```python
def build_mpg123_command(track_path, volume_factor, skip_frames=None):
    """Arma el comando de mpg123 aplicando el volumen actual y, si se pasa
    skip_frames, arrancando desde ese punto (usado al reanudar)."""
    cmd = ["mpg123", "-q", "-f", str(volume_factor)]
    if skip_frames is not None:
        cmd += ["-k", str(skip_frames)]
    cmd += ["--audiodevice", "plughw:0,0", track_path]
    return cmd
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_volume.py -v`
Expected: 5 passed.

- [ ] **Step 5: Wire the volume factor into `load_track`**

Find (in `load_track`):
```python
    current_process = subprocess.Popen(
        ["mpg123", "-q", "--audiodevice", "plughw:0,0", track_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

Replace with:
```python
    volume_factor = get_volume_scale_factor()
    current_process = subprocess.Popen(
        build_mpg123_command(track_path, volume_factor),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

- [ ] **Step 6: Wire the volume factor into `_resume_now`**

Find (in `_resume_now`):
```python
    current_process = subprocess.Popen(
        ["mpg123", "-q", "-k", str(skip_frames), "--audiodevice", "plughw:0,0", track_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

Replace with:
```python
    volume_factor = get_volume_scale_factor()
    current_process = subprocess.Popen(
        build_mpg123_command(track_path, volume_factor, skip_frames=skip_frames),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

- [ ] **Step 7: Write an integration test for the wiring**

Create `tests/test_load_track.py`:
```python
import json

import daemon


def test_load_track_applies_current_volume_factor(tmp_path, monkeypatch, fake_popen):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 50}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)

    daemon.current_album = "test-album"
    daemon.current_tracks = ["01 - Song.mp3"]

    daemon.load_track(0)

    assert len(fake_popen.instances) == 1
    cmd = fake_popen.instances[0].args
    expected_factor = str(int(50 / 100 * 32768))
    assert cmd[:4] == ["mpg123", "-q", "-f", expected_factor]
```

- [ ] **Step 8: Run to verify it passes**

Run: `pytest tests/test_load_track.py tests/test_volume.py -v`
Expected: all passed.

- [ ] **Step 9: Confirm the frontend slider is already wired (no code change expected)**

Read [static/js/app.js](../../../static/js/app.js) around the `setVolume` function and the `volumeSlider` `change` listener — it already `POST`s to `/api/volume` with `{ volume: val }` on release, and `/api/volume` in `app.py` already saves it to `config["volume"]`. This is already correct; no change needed. If, when manually testing in Step 10, the slider doesn't visibly move mpg123's output volume, re-check that `daemon.py`'s systemd service was restarted to pick up the new code — this is not a frontend bug.

- [ ] **Step 10: Manual verification on the Pi**

After deploying, place a disc, then move the volume slider in the webapp and confirm (by ear) that the next track load or resume plays measurably quieter/louder. Exact command to sanity-check the factor by hand: `mpg123 -f 16384 --audiodevice plughw:0,0 albums/<album>/<track>.mp3` should play at roughly half volume vs. no `-f` flag.

- [ ] **Step 11: Commit**

```bash
git add daemon.py tests/test_volume.py tests/test_load_track.py
git commit -m "feat: software volume control via mpg123 -f factor"
```

---

### Task 3: Battery reading (INA219)

**Files:**
- Modify: `daemon.py` (add `battery_percent`, `read_battery`, `update_battery_config`, `init_battery`, `battery_ticker`; start the thread in `main()`)
- Test: `tests/test_battery.py`

**Interfaces:**
- Consumes: `read_config()`, `write_full_config()` (existing).
- Produces: `daemon.battery_percent(voltage: float) -> int`, `daemon.read_battery(ina) -> dict` (shape `{"percent": int, "charging": bool}`), `daemon.update_battery_config(ina) -> None` (writes `config["battery"]`), `daemon.init_battery() -> INA219`, `daemon.battery_ticker(ina) -> None` (infinite loop, run in a daemon thread). Task 4 (`app.py`) will read `config["battery"]` with this exact shape.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_battery.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_battery.py -v`
Expected: FAIL with `AttributeError: module 'daemon' has no attribute 'battery_percent'`.

- [ ] **Step 3: Add the `ina219` import**

Find (top of `daemon.py`):
```python
from adafruit_pn532.i2c import PN532_I2C
from mutagen.mp3 import MP3
```

Replace with:
```python
from adafruit_pn532.i2c import PN532_I2C
from mutagen.mp3 import MP3
from ina219 import INA219
```

- [ ] **Step 4: Add the battery constant near the other constants**

Find:
```python
MOTOR_PINS  = [5, 6, 13, 26]
MOTOR_DELAY = 0.002
```

Replace with:
```python
MOTOR_PINS  = [5, 6, 13, 26]
MOTOR_DELAY = 0.002

BATTERY_POLL_INTERVAL = 7  # segundos
BATTERY_VOLTAGE_EMPTY = 3.0
BATTERY_VOLTAGE_FULL  = 4.2
```

- [ ] **Step 5: Implement the battery functions**

Add a new section after `# ── Motor ─────` block (right before `# ── Pistas ───`):
```python
# ── Batería (UPS HAT, INA219) ─────────────────
def battery_percent(voltage):
    span = BATTERY_VOLTAGE_FULL - BATTERY_VOLTAGE_EMPTY
    pct = round((voltage - BATTERY_VOLTAGE_EMPTY) / span * 100)
    return max(0, min(100, pct))

def read_battery(ina):
    voltage = ina.voltage()
    current = ina.current()
    return {"percent": battery_percent(voltage), "charging": current > 0}

def update_battery_config(ina):
    battery = read_battery(ina)
    config = read_config()
    config["battery"] = battery
    write_full_config(config)

def init_battery():
    ina = INA219(shunt_ohms=0.1, address=0x43, busnum=1)
    ina.configure()
    print("[ECO] Sensor de batería (INA219) listo")
    return ina

def battery_ticker(ina):
    while True:
        try:
            update_battery_config(ina)
        except Exception as e:
            print(f"[ECO] Error leyendo batería: {e}")
        time.sleep(BATTERY_POLL_INTERVAL)
```

- [ ] **Step 6: Run to verify it passes**

Run: `pytest tests/test_battery.py -v`
Expected: 8 passed.

- [ ] **Step 7: Start the battery thread from `main()`**

Find:
```python
    pn532 = init_nfc()
    init_motor()
    write_state(None, 0, None, 0, False, 0, 0)

    ticker = threading.Thread(target=progress_ticker, daemon=True)
    ticker.start()
```

Replace with:
```python
    pn532 = init_nfc()
    init_motor()
    write_state(None, 0, None, 0, False, 0, 0)

    ticker = threading.Thread(target=progress_ticker, daemon=True)
    ticker.start()

    ina = init_battery()
    update_battery_config(ina)  # primer valor disponible de inmediato, sin esperar al primer tick
    battery_thread = threading.Thread(target=battery_ticker, args=(ina,), daemon=True)
    battery_thread.start()
```

- [ ] **Step 8: Manual verification on the Pi**

Run `daemon.py` for a few seconds and check `config.json` picks up a `"battery"` key:
```bash
python3 daemon.py &
sleep 3
python3 -c "import json; print(json.load(open('config.json'))['battery'])"
```
Expected: something like `{"percent": 78, "charging": False}` with a plausible percent for the UPS HAT's current charge.

- [ ] **Step 9: Commit**

```bash
git add daemon.py tests/test_battery.py
git commit -m "feat: read battery percentage/charging state from INA219 into config.json"
```

---

### Task 4: Expose battery in `/api/status` + frontend indicator

**Files:**
- Modify: `app.py` (`/api/status`)
- Modify: `templates/index.html` (home header)
- Modify: `static/js/app.js` (render battery)
- Modify: `static/css/style.css` (battery styles)
- Test: `tests/test_app_status.py`

**Interfaces:**
- Consumes: `config["battery"]` shape `{"percent": int, "charging": bool}` from Task 3, defaulting to `{"percent": None, "charging": False}` when absent (daemon not running yet, or old `config.json`).
- Produces: `/api/status` response gains a `"battery"` key with that shape; frontend `state.battery`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app_status.py`:
```python
import json

import app as app_module


def _base_config(extra=None):
    config = {
        "albums": {}, "volume": 70, "command": None,
        "now_playing": {"album": None, "track": 0, "track_name": None, "total": 0, "playing": False},
    }
    if extra:
        config.update(extra)
    return config


def test_status_includes_battery_field(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_base_config({"battery": {"percent": 42, "charging": True}})))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))
    client = app_module.app.test_client()

    res = client.get("/api/status")

    assert res.get_json()["battery"] == {"percent": 42, "charging": True}


def test_status_defaults_battery_when_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(_base_config()))
    monkeypatch.setattr(app_module, "CONFIG_PATH", str(config_path))
    client = app_module.app.test_client()

    res = client.get("/api/status")

    assert res.get_json()["battery"] == {"percent": None, "charging": False}
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_app_status.py -v`
Expected: FAIL with `KeyError: 'battery'`.

- [ ] **Step 3: Add the field in `app.py`**

Find:
```python
        "volume":       config.get("volume", 70),
        "albums":       list(config.get("albums", {}).values()),
```

Replace with:
```python
        "volume":       config.get("volume", 70),
        "battery":      config.get("battery", {"percent": None, "charging": False}),
        "albums":       list(config.get("albums", {}).values()),
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_app_status.py -v`
Expected: 2 passed.

- [ ] **Step 5: Add the battery indicator markup**

In [templates/index.html](../../../templates/index.html), find:
```html
      <button class="settings-btn" id="settings-btn" aria-label="Ajustes">
```

Replace the whole header block:
```html
    <header class="app-header">
      <div class="app-title">
        <p class="app-label">Tu música</p>
        <h1 class="app-name serif">Eco <em>Records</em></h1>
      </div>
      <button class="settings-btn" id="settings-btn" aria-label="Ajustes">
```

with:
```html
    <header class="app-header">
      <div class="app-title">
        <p class="app-label">Tu música</p>
        <h1 class="app-name serif">Eco <em>Records</em></h1>
      </div>
      <div class="header-actions">
        <div class="battery-indicator" id="battery-indicator" hidden>
          <svg class="battery-icon" width="20" height="11" viewBox="0 0 20 11" fill="none" stroke="currentColor" stroke-width="1.2" aria-hidden="true">
            <rect x="0.6" y="0.6" width="16.5" height="9.8" rx="2"/>
            <rect x="18" y="3.5" width="1.6" height="4" rx="0.8" fill="currentColor" stroke="none"/>
            <rect class="battery-icon-fill" id="battery-icon-fill" x="2.2" y="2.2" width="0" height="6.6" rx="1"/>
          </svg>
          <span class="battery-pct" id="battery-pct">—</span>
        </div>
        <button class="settings-btn" id="settings-btn" aria-label="Ajustes">
```

Then, right after the closing `</button>` of `settings-btn` (still inside `.app-header`), close the new wrapper:

Find:
```html
      </button>
    </header>

    <section class="disc-section" aria-label="Disco actual">
```

Replace with:
```html
      </button>
      </div>
    </header>

    <section class="disc-section" aria-label="Disco actual">
```

- [ ] **Step 6: Add battery styles**

In [static/css/style.css](../../../static/css/style.css), find:
```css
.settings-btn {
```

Insert immediately before it:
```css
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.battery-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
}

.battery-icon-fill {
  fill: var(--text-secondary);
  transition: width 0.3s ease, fill 0.3s ease;
}

.battery-pct {
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}

.battery-indicator.low .battery-icon,
.battery-indicator.low .battery-pct {
  color: #8B2020;
}

.battery-indicator.low .battery-icon-fill {
  fill: #8B2020;
}

.battery-indicator.charging .battery-pct::after {
  content: ' ⚡';
}

.settings-btn {
```

- [ ] **Step 7: Render battery state in `app.js`**

In [static/js/app.js](../../../static/js/app.js), find:
```js
const state = {
  playing: false,
  volume: 70,
```

Replace with:
```js
const state = {
  playing: false,
  volume: 70,
  battery: { percent: null, charging: false },
```

Find:
```js
  volumeSlider:   $('volume-slider'),
  volumeDisplay:  $('volume-display'),
  albumsList:     $('albums-list'),
}
```

Replace with:
```js
  volumeSlider:   $('volume-slider'),
  volumeDisplay:  $('volume-display'),
  albumsList:     $('albums-list'),
  batteryIndicator: $('battery-indicator'),
  batteryFill:      $('battery-icon-fill'),
  batteryPct:       $('battery-pct'),
}
```

Find:
```js
    state.volume      = data.volume
```

Replace with:
```js
    state.volume      = data.volume
    state.battery     = data.battery || { percent: null, charging: false }
```

Find:
```js
  if (!state.draggingVolume) renderVolume(state.volume)
  renderProgress()
```

Replace with:
```js
  if (!state.draggingVolume) renderVolume(state.volume)
  renderProgress()
  renderBattery()
```

Add the new function right after `renderVolume`:
```js
function renderBattery() {
  const { percent, charging } = state.battery
  if (percent === null || percent === undefined) {
    els.batteryIndicator.hidden = true
    return
  }
  els.batteryIndicator.hidden = false
  els.batteryPct.textContent = percent + '%'
  const clamped = Math.max(0, Math.min(100, percent))
  els.batteryFill.setAttribute('width', (clamped / 100 * 12.6).toFixed(1))
  els.batteryIndicator.classList.toggle('low', percent < 20)
  els.batteryIndicator.classList.toggle('charging', charging)
}
```

- [ ] **Step 8: Manual verification in the browser**

Run `python app.py` on the dev machine (Flask has no hardware dependency), with a scratch `config.json` containing `"battery": {"percent": 15, "charging": true}` next to it, open `http://localhost:5000`, and confirm: the battery icon appears next to the settings gear, shows "15%" in the low-battery red color, and the "⚡" charging marker appears. Then edit the file to `"percent": 80, "charging": false` and reload — icon should turn back to the normal secondary-text color with no "⚡".

- [ ] **Step 9: Commit**

```bash
git add app.py templates/index.html static/js/app.js static/css/style.css tests/test_app_status.py
git commit -m "feat: expose and render battery percentage/charging indicator"
```

---

### Task 5: Playback history logging

**Files:**
- Modify: `daemon.py` (add `read_history`, `write_history`, `log_history`; call from `load_track`)
- Modify: `tests/test_load_track.py` (stub the new call so the Task 2 test keeps passing)
- Modify: `.gitignore`
- Test: `tests/test_history.py`

**Interfaces:**
- Produces: `daemon.HISTORY_PATH`, `daemon.log_history(album: str, track_name: str) -> None`, writing to `history.json` a list of `{"album": str, "track_name": str, "timestamp": float}`, capped at 50 entries, oldest dropped first.
- Consumes: nothing new from other tasks.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_history.py`:
```python
import json

import daemon


def test_log_history_appends_entry(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon.time, "time", lambda: 1700000000.0)

    daemon.log_history("thriller", "Beat It")

    saved = json.loads(history_path.read_text())
    assert saved == [{"album": "thriller", "track_name": "Beat It", "timestamp": 1700000000.0}]


def test_log_history_appends_to_existing_file(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps([{"album": "a", "track_name": "t1", "timestamp": 1.0}]))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon.time, "time", lambda: 2.0)

    daemon.log_history("b", "t2")

    saved = json.loads(history_path.read_text())
    assert saved == [
        {"album": "a", "track_name": "t1", "timestamp": 1.0},
        {"album": "b", "track_name": "t2", "timestamp": 2.0},
    ]


def test_log_history_caps_at_50_entries(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    existing = [{"album": "a", "track_name": f"t{i}", "timestamp": float(i)} for i in range(50)]
    history_path.write_text(json.dumps(existing))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(daemon.time, "time", lambda: 999.0)

    daemon.log_history("a", "newest")

    saved = json.loads(history_path.read_text())
    assert len(saved) == 50
    assert saved[-1] == {"album": "a", "track_name": "newest", "timestamp": 999.0}
    assert saved[0]["track_name"] == "t1"  # se descartó t0, la más vieja
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_history.py -v`
Expected: FAIL with `AttributeError: module 'daemon' has no attribute 'HISTORY_PATH'`.

- [ ] **Step 3: Implement history storage in `daemon.py`**

Find:
```python
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")
```

Replace with:
```python
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH  = os.path.join(BASE_DIR, "albums")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")

HISTORY_LIMIT = 50
```

Add a new section right after `# ── Config ───` block (before `# ── NFC ───`):
```python
# ── Historial de reproducción ─────────────────
def read_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)

def write_history(history):
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)

def log_history(album, track_name):
    history = read_history()
    history.append({"album": album, "track_name": track_name, "timestamp": time.time()})
    write_history(history[-HISTORY_LIMIT:])
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_history.py -v`
Expected: 3 passed.

- [ ] **Step 5: Call `log_history` from `load_track`**

Find (in `load_track`):
```python
    track_name = clean_track_name(current_tracks[index])
    print(f"[ECO] Reproduciendo: {track_name} ({current_duration}s)")
    write_state(current_album, index + 1, track_name, len(current_tracks), True, 0, current_duration)
```

Replace with:
```python
    track_name = clean_track_name(current_tracks[index])
    print(f"[ECO] Reproduciendo: {track_name} ({current_duration}s)")
    log_history(current_album, track_name)
    write_state(current_album, index + 1, track_name, len(current_tracks), True, 0, current_duration)
```

- [ ] **Step 6: Update the Task 2 integration test to tolerate the new side effect**

`load_track` now also writes `history.json` in the real project directory unless redirected — `tests/test_load_track.py`'s existing test doesn't monkeypatch `HISTORY_PATH`, so it would write into the real repo's `history.json`. Fix it.

Find (in `tests/test_load_track.py`):
```python
def test_load_track_applies_current_volume_factor(tmp_path, monkeypatch, fake_popen):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 50}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
```

Replace with:
```python
def test_load_track_applies_current_volume_factor(tmp_path, monkeypatch, fake_popen):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"volume": 50}))
    monkeypatch.setattr(daemon, "CONFIG_PATH", str(config_path))
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
```

- [ ] **Step 7: Run to verify both still pass**

Run: `pytest tests/test_load_track.py tests/test_history.py -v`
Expected: all passed.

- [ ] **Step 8: Ignore the generated file**

In [.gitignore](../../../.gitignore), find:
```
# Configuración con datos reales (UIDs de tags)
# config.json   ← lo dejamos SIN comentar por ahora, subimos el de ejemplo
```

Replace with:
```
# Configuración con datos reales (UIDs de tags)
# config.json   ← lo dejamos SIN comentar por ahora, subimos el de ejemplo

# Datos generados en runtime (a diferencia de config.json, no hay versión de ejemplo)
history.json
stats.json
.filter_cache/
```

- [ ] **Step 9: Manual verification on the Pi**

Play a couple of tracks, then:
```bash
python3 -c "import json; print(json.load(open('history.json')))"
```
Expected: a list of `{"album": ..., "track_name": ..., "timestamp": ...}` entries, most recent last.

- [ ] **Step 10: Commit**

```bash
git add daemon.py tests/test_history.py tests/test_load_track.py .gitignore
git commit -m "feat: log playback history to history.json, capped at 50 entries"
```

---

### Task 6: `/api/history` route + "Escuchado recientemente" UI

**Files:**
- Modify: `app.py` (new `/api/history` route)
- Modify: `templates/index.html` (Discos view)
- Modify: `static/js/app.js` (`loadLibraryExtras`, `renderHistory`, `timeAgo`)
- Modify: `static/css/style.css`
- Test: `tests/test_app_history.py`

**Interfaces:**
- Consumes: `history.json` shape from Task 5 (`{"album": str, "track_name": str, "timestamp": float}`).
- Produces: `GET /api/history` → JSON list, most recent first. Frontend function `loadLibraryExtras()` (Task 8 extends it, doesn't replace it).

- [ ] **Step 1: Write the failing test**

Create `tests/test_app_history.py`:
```python
import json

import app as app_module


def test_history_route_returns_most_recent_first(tmp_path, monkeypatch):
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps([
        {"album": "a", "track_name": "t1", "timestamp": 1.0},
        {"album": "b", "track_name": "t2", "timestamp": 2.0},
    ]))
    monkeypatch.setattr(app_module, "HISTORY_PATH", str(history_path))
    client = app_module.app.test_client()

    res = client.get("/api/history")

    assert res.get_json() == [
        {"album": "b", "track_name": "t2", "timestamp": 2.0},
        {"album": "a", "track_name": "t1", "timestamp": 1.0},
    ]


def test_history_route_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "HISTORY_PATH", str(tmp_path / "missing.json"))
    client = app_module.app.test_client()

    res = client.get("/api/history")

    assert res.get_json() == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_app_history.py -v`
Expected: FAIL with `AttributeError: module 'app' has no attribute 'HISTORY_PATH'`.

- [ ] **Step 3: Add the route**

Find (in `app.py`):
```python
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")
```

Replace with:
```python
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH  = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH  = os.path.join(BASE_DIR, "albums")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
```

Find:
```python
# ── API: cambiar volumen ──────────────────────
```

Insert immediately before it:
```python
# ── API: historial de reproducción ────────────
@app.route("/api/history")
def get_history():
    if not os.path.exists(HISTORY_PATH):
        return jsonify([])
    with open(HISTORY_PATH, "r") as f:
        history = json.load(f)
    return jsonify(list(reversed(history)))

# ── API: cambiar volumen ──────────────────────
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_app_history.py -v`
Expected: 2 passed.

- [ ] **Step 5: Add the "Escuchado recientemente" markup**

In `templates/index.html`, find:
```html
    <div class="albums-list" id="albums-list">
      <!-- Se llena desde JS -->
    </div>
```

Replace with:
```html
    <div class="library-extra" id="library-extra">
      <div class="stats-highlight" id="stats-highlight" hidden>
        <span class="stats-highlight-label">Más escuchado</span>
        <span class="stats-highlight-value" id="stats-top-album">—</span>
      </div>

      <div class="history-section" id="history-section" hidden>
        <p class="section-heading">Escuchado recientemente</p>
        <div class="history-list" id="history-list"></div>
      </div>
    </div>

    <div class="albums-list" id="albums-list">
      <!-- Se llena desde JS -->
    </div>
```

(`.stats-highlight` is wired up in Task 8; it's added here already, `hidden`, so this task's HTML doesn't need a second edit later.)

- [ ] **Step 6: Add styles**

In `static/css/style.css`, find:
```css
/* ── Albums list (vista Discos) ────────────── */
```

Insert immediately before it:
```css
/* ── Biblioteca: destacado de stats + historial ─ */
.library-extra {
  padding: 4px 18px 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.stats-highlight {
  background: var(--accent-bg);
  border: 1px solid var(--accent);
  border-radius: var(--radius-btn);
  padding: 10px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-highlight-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-dark);
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.stats-highlight-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-heading {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.4px;
  margin-bottom: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-card);
  border-radius: 12px;
  border: 1px solid var(--border);
}

.history-item-text {
  min-width: 0;
}

.history-item-track {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-item-album {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
}

.history-item-time {
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* ── Albums list (vista Discos) ────────────── */
```

- [ ] **Step 7: Fetch and render in `app.js`**

Find:
```js
function navigateTo(view) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'))
  document.getElementById('view-' + view).classList.add('active')
  document.querySelectorAll('.nav-item').forEach(btn => {
    const isActive = btn.dataset.view === view
    btn.classList.toggle('active', isActive)
    btn.querySelector('.nav-icon-wrap').classList.toggle('active', isActive)
  })
  state.currentView = view
  if (view === 'discos') loadAlbums()
}
```

Replace with:
```js
function navigateTo(view) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'))
  document.getElementById('view-' + view).classList.add('active')
  document.querySelectorAll('.nav-item').forEach(btn => {
    const isActive = btn.dataset.view === view
    btn.classList.toggle('active', isActive)
    btn.querySelector('.nav-icon-wrap').classList.toggle('active', isActive)
  })
  state.currentView = view
  if (view === 'discos') { loadAlbums(); loadLibraryExtras() }
}
```

Add near the bottom of the `// VISTA: DISCOS` section, right before `async function showAlbumDetail`:
```js
function timeAgo(timestamp) {
  const diffMin = Math.floor((Date.now() / 1000 - timestamp) / 60)
  if (diffMin < 1) return 'ahora'
  if (diffMin < 60) return `hace ${diffMin} min`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `hace ${diffH} h`
  return `hace ${Math.floor(diffH / 24)} d`
}

async function loadLibraryExtras() {
  try {
    const [albumsRes, historyRes] = await Promise.all([
      fetch('/api/albums'), fetch('/api/history'),
    ])
    const albums  = await albumsRes.json()
    const history = await historyRes.json()

    const albumNames = {}
    albums.forEach(a => { albumNames[a.id] = a.name })

    renderHistory(history, albumNames)
  } catch (err) { console.warn('Error cargando historial:', err) }
}

function renderHistory(history, albumNames) {
  const section = $('history-section')
  if (!history.length) { section.hidden = true; return }
  section.hidden = false
  $('history-list').innerHTML = history.slice(0, 8).map(entry => `
    <div class="history-item">
      <div class="history-item-text">
        <p class="history-item-track">${entry.track_name || '—'}</p>
        <p class="history-item-album">${albumNames[entry.album] || entry.album}</p>
      </div>
      <span class="history-item-time">${timeAgo(entry.timestamp)}</span>
    </div>
  `).join('')
}
```

- [ ] **Step 8: Manual verification in the browser**

Run `python app.py` locally with a scratch `history.json` containing a few entries and a matching `config.json`/`albums/` (or just entries whose `album` won't match any id — the fallback to the raw id is exercised then). Open the Discos view and confirm the "Escuchado recientemente" list renders, most recent first, with relative times.

- [ ] **Step 9: Commit**

```bash
git add app.py templates/index.html static/js/app.js static/css/style.css tests/test_app_history.py
git commit -m "feat: expose playback history via /api/history and show it in the Discos view"
```

---

### Task 7: Usage stats counting

**Files:**
- Modify: `daemon.py` (add `read_stats`, `write_stats`, `increment_album_stat`; call from `play_album`)
- Test: `tests/test_stats.py`

**Interfaces:**
- Produces: `daemon.STATS_PATH`, `daemon.increment_album_stat(album: str) -> None`, writing to `stats.json` a flat `{"album_id": play_count}` dict.
- Consumes: nothing new from other tasks. Called once per fresh disc placement (`play_album`), never on `next`/`prev`, matching the spec's "avoid counting every track change within the same album".

- [ ] **Step 1: Write the failing tests**

Create `tests/test_stats.py`:
```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_stats.py -v`
Expected: FAIL with `AttributeError: module 'daemon' has no attribute 'increment_album_stat'`.

- [ ] **Step 3: Implement stats storage in `daemon.py`**

Find:
```python
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")

HISTORY_LIMIT = 50
```

Replace with:
```python
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
STATS_PATH   = os.path.join(BASE_DIR, "stats.json")

HISTORY_LIMIT = 50
```

Add a new section right after the history section (before `# ── NFC ───`):
```python
# ── Estadísticas de uso ───────────────────────
def read_stats():
    if not os.path.exists(STATS_PATH):
        return {}
    with open(STATS_PATH, "r") as f:
        return json.load(f)

def write_stats(stats):
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, indent=2)

def increment_album_stat(album):
    stats = read_stats()
    stats[album] = stats.get(album, 0) + 1
    write_stats(stats)
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_stats.py -v`
Expected: 2 passed.

- [ ] **Step 5: Call it once per fresh album play in `play_album`**

Find:
```python
def play_album(album_name):
    """NFC identificó el álbum: reproduce directo (sin esperar Hall)."""
    global current_album, current_tracks, current_index

    tracks = get_tracks(album_name)
    if not tracks:
        print(f"[ECO] Sin pistas en: {album_name}")
        write_state(album_name, 0, None, 0, False)
        return

    current_album  = album_name
    current_tracks = tracks
    current_index  = 0
    load_track(0)
    start_motor()
```

Replace with:
```python
def play_album(album_name):
    """NFC identificó el álbum: reproduce directo (sin esperar Hall)."""
    global current_album, current_tracks, current_index

    tracks = get_tracks(album_name)
    if not tracks:
        print(f"[ECO] Sin pistas en: {album_name}")
        write_state(album_name, 0, None, 0, False)
        return

    increment_album_stat(album_name)
    current_album  = album_name
    current_tracks = tracks
    current_index  = 0
    load_track(0)
    start_motor()
```

- [ ] **Step 6: Write a test proving `next_track`/`prev_track` don't double-count**

Add to `tests/test_stats.py`:
```python
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

    daemon.play_album("thriller")
    daemon.next_track()

    assert json.loads(stats_path.read_text()) == {"thriller": 1}
```

- [ ] **Step 7: Run to verify it passes**

Run: `pytest tests/test_stats.py -v`
Expected: 3 passed.

- [ ] **Step 8: Manual verification on the Pi**

Place the same disc twice (removing it in between so the daemon's `current_uid` debounce resets), then:
```bash
python3 -c "import json; print(json.load(open('stats.json')))"
```
Expected: the album's counter is `2`.

- [ ] **Step 9: Commit**

```bash
git add daemon.py tests/test_stats.py
git commit -m "feat: count album plays in stats.json, once per fresh disc placement"
```

---

### Task 8: `/api/stats` route + "Más escuchado" UI

**Files:**
- Modify: `app.py` (new `/api/stats` route)
- Modify: `static/js/app.js` (`loadLibraryExtras`, `renderStatsHighlight`)
- Test: `tests/test_app_stats.py`

**Interfaces:**
- Consumes: `stats.json` shape from Task 7 (`{"album_id": count}`).
- Produces: `GET /api/stats` → `{"albums": {...}, "top_album": str | None}`. Extends the `loadLibraryExtras()` function from Task 6.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app_stats.py`:
```python
import json

import app as app_module


def test_stats_route_returns_top_album(tmp_path, monkeypatch):
    stats_path = tmp_path / "stats.json"
    stats_path.write_text(json.dumps({"thriller": 5, "02-09": 2}))
    monkeypatch.setattr(app_module, "STATS_PATH", str(stats_path))
    client = app_module.app.test_client()

    res = client.get("/api/stats")

    assert res.get_json() == {"albums": {"thriller": 5, "02-09": 2}, "top_album": "thriller"}


def test_stats_route_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "STATS_PATH", str(tmp_path / "missing.json"))
    client = app_module.app.test_client()

    res = client.get("/api/stats")

    assert res.get_json() == {"albums": {}, "top_album": None}
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_app_stats.py -v`
Expected: FAIL with `AttributeError: module 'app' has no attribute 'STATS_PATH'`.

- [ ] **Step 3: Add the route**

Find (in `app.py`):
```python
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
```

Replace with:
```python
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")
STATS_PATH   = os.path.join(BASE_DIR, "stats.json")
```

Find:
```python
# ── API: cambiar volumen ──────────────────────
```

Insert immediately before it:
```python
# ── API: estadísticas de uso ──────────────────
@app.route("/api/stats")
def get_stats():
    if not os.path.exists(STATS_PATH):
        return jsonify({"albums": {}, "top_album": None})
    with open(STATS_PATH, "r") as f:
        stats = json.load(f)
    top_album = max(stats, key=stats.get) if stats else None
    return jsonify({"albums": stats, "top_album": top_album})

# ── API: cambiar volumen ──────────────────────
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_app_stats.py -v`
Expected: 2 passed.

- [ ] **Step 5: Extend `loadLibraryExtras` in `app.js`**

Find:
```js
async function loadLibraryExtras() {
  try {
    const [albumsRes, historyRes] = await Promise.all([
      fetch('/api/albums'), fetch('/api/history'),
    ])
    const albums  = await albumsRes.json()
    const history = await historyRes.json()

    const albumNames = {}
    albums.forEach(a => { albumNames[a.id] = a.name })

    renderHistory(history, albumNames)
  } catch (err) { console.warn('Error cargando historial:', err) }
}
```

Replace with:
```js
async function loadLibraryExtras() {
  try {
    const [albumsRes, historyRes, statsRes] = await Promise.all([
      fetch('/api/albums'), fetch('/api/history'), fetch('/api/stats'),
    ])
    const albums  = await albumsRes.json()
    const history = await historyRes.json()
    const stats   = await statsRes.json()

    const albumNames = {}
    albums.forEach(a => { albumNames[a.id] = a.name })

    renderStatsHighlight(stats, albumNames)
    renderHistory(history, albumNames)
  } catch (err) { console.warn('Error cargando historial/estadísticas:', err) }
}

function renderStatsHighlight(stats, albumNames) {
  const el = $('stats-highlight')
  if (!stats.top_album) { el.hidden = true; return }
  el.hidden = false
  $('stats-top-album').textContent = albumNames[stats.top_album] || stats.top_album
}
```

- [ ] **Step 6: Manual verification in the browser**

With a scratch `stats.json` (e.g. `{"thriller": 5, "02-09": 2}`) and matching `/api/albums` data, open the Discos view and confirm the "Más escuchado" pill shows the display name of `thriller`. Empty `stats.json` (or none) should hide the pill entirely, not show "—" or "null".

- [ ] **Step 7: Commit**

```bash
git add app.py static/js/app.js tests/test_app_stats.py
git commit -m "feat: expose usage stats via /api/stats and show top album in the Discos view"
```

---

### Task 9: Bass high-pass filter (sox, cached)

**Decision (per spec's "evaluate before implementing"):** use `sox` to pre-filter each track to a cached copy the first time it's played, rather than mpg123's own CLI (mpg123 has no documented, stable equalizer flag worth depending on) or filtering on every single play (too much CPU for a Pi Zero 2W on repeat plays of the same track). Filtering mp3→mp3 (not mp3→wav→mp3) keeps the existing `-k` resume frame-skip math in `_resume_now` valid unchanged, since sox's `highpass` doesn't change the sample rate.

**Files:**
- Modify: `daemon.py` (add `get_filtered_track_path`, `_filter_cache_path`; wire into `load_track` and `_resume_now`)
- Modify: `README.md` (add `sox` to the install line)
- Test: `tests/test_audio_filter.py`

**Interfaces:**
- Consumes: `build_mpg123_command` from Task 2 (its first argument becomes the filtered path instead of the original one).
- Produces: `daemon.FILTER_CACHE_DIR`, `daemon.HIGHPASS_HZ`, `daemon.get_filtered_track_path(track_path: str) -> str` (returns the cached filtered path, or the original `track_path` unchanged if filtering fails for any reason — playback must never break because of this feature).

- [ ] **Step 0: Install `sox` on the Pi (manual, cannot be done from this dev machine)**

```bash
sudo apt update
sudo apt install -y sox libsox-fmt-mp3
sox --version
```
Expected: a version string, no error. `libsox-fmt-mp3` is required for `sox` to read/write `.mp3` directly — without it `sox` can still run but will fail specifically on mp3 input/output.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_audio_filter.py`:
```python
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
    assert "highpass" in calls[0]
    assert str(daemon.HIGHPASS_HZ) in calls[0]


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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_audio_filter.py -v`
Expected: FAIL with `AttributeError: module 'daemon' has no attribute '_filter_cache_path'`.

- [ ] **Step 3: Implement the filter cache in `daemon.py`**

Find:
```python
import json
import os
import time
import subprocess
import threading
```

Replace with:
```python
import hashlib
import json
import os
import time
import subprocess
import threading
```

Find:
```python
BATTERY_POLL_INTERVAL = 7  # segundos
BATTERY_VOLTAGE_EMPTY = 3.0
BATTERY_VOLTAGE_FULL  = 4.2
```

Replace with:
```python
BATTERY_POLL_INTERVAL = 7  # segundos
BATTERY_VOLTAGE_EMPTY = 3.0
BATTERY_VOLTAGE_FULL  = 4.2

FILTER_CACHE_DIR = os.path.join(BASE_DIR, ".filter_cache")
HIGHPASS_HZ      = 120
```

Add a new section right before `# ── Control de audio (proceso limpio por pista) ──`:
```python
# ── Filtro de graves (pasa-altos, cacheado) ───
def _filter_cache_path(track_path):
    mtime = int(os.path.getmtime(track_path))
    key = f"{track_path}|{mtime}|{HIGHPASS_HZ}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(FILTER_CACHE_DIR, f"{digest}.mp3")

def get_filtered_track_path(track_path):
    """Pasa-altos suave (~120Hz) para reducir distorsión de graves en
    parlantes chicos. Se cachea: solo se filtra la primera vez que se
    reproduce cada pista. Si el filtro falla por lo que sea, se reproduce
    el original — esta función nunca debe romper la reproducción."""
    os.makedirs(FILTER_CACHE_DIR, exist_ok=True)
    cache_path = _filter_cache_path(track_path)

    if os.path.exists(cache_path):
        return cache_path

    try:
        subprocess.run(
            ["sox", track_path, cache_path, "highpass", str(HIGHPASS_HZ)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return cache_path
    except Exception as e:
        print(f"[ECO] Filtro de graves falló, reproduciendo original: {e}")
        return track_path
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_audio_filter.py -v`
Expected: 5 passed.

- [ ] **Step 5: Wire it into `load_track`**

Find:
```python
    volume_factor = get_volume_scale_factor()
    current_process = subprocess.Popen(
        build_mpg123_command(track_path, volume_factor),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

Replace with:
```python
    volume_factor = get_volume_scale_factor()
    playback_path = get_filtered_track_path(track_path)
    current_process = subprocess.Popen(
        build_mpg123_command(playback_path, volume_factor),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

- [ ] **Step 6: Wire it into `_resume_now`**

Find:
```python
    volume_factor = get_volume_scale_factor()
    current_process = subprocess.Popen(
        build_mpg123_command(track_path, volume_factor, skip_frames=skip_frames),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

Replace with:
```python
    volume_factor = get_volume_scale_factor()
    playback_path = get_filtered_track_path(track_path)
    current_process = subprocess.Popen(
        build_mpg123_command(playback_path, volume_factor, skip_frames=skip_frames),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
```

- [ ] **Step 7: Update `tests/test_load_track.py` so it doesn't try to run real `sox`**

Find:
```python
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
```

Replace with:
```python
    monkeypatch.setattr(daemon, "HISTORY_PATH", str(tmp_path / "history.json"))
    monkeypatch.setattr(daemon, "get_duration", lambda path: 180)
    monkeypatch.setattr(daemon, "get_filtered_track_path", lambda path: path)
```

- [ ] **Step 8: Run the full suite**

Run: `pytest -v`
Expected: all passed.

- [ ] **Step 9: Document the new system dependency**

In `README.md`, find:
```
pip install flask adafruit-circuitpython-pn532 mutagen RPi.GPIO gpiozero lgpio yt-dlp pi-ina219
```

Replace with:
```
sudo apt install -y sox libsox-fmt-mp3
pip install flask adafruit-circuitpython-pn532 mutagen RPi.GPIO gpiozero lgpio yt-dlp pi-ina219
```

- [ ] **Step 10: Manual verification on the Pi (this is the part that actually matters — automated tests can't judge audio quality)**

Play a bass-heavy track that's known to distort on the current speakers. Confirm:
1. First play takes a brief, noticeable extra moment before sound starts (the `sox` pass running) — check `.filter_cache/` now has one new `.mp3` file.
2. Replaying the same track (skip back to it, or reload the album) starts as fast as before filtering existed — the cache hit path.
3. By ear, the bass distortion/rattle is reduced without the track sounding thin.
4. Pause/resume (`-k` skip) on a filtered track still resumes at roughly the right position — the frame-skip math wasn't affected by filtering.

If step 3 isn't convincing, adjust `HIGHPASS_HZ` (try 100 or 150) and delete `.filter_cache/` to force re-filtering, then re-test — this constant is a starting point from the spec's suggested 100-150Hz range, not a value verified on the real speakers from this dev machine.

- [ ] **Step 11: Commit**

```bash
git add daemon.py README.md tests/test_audio_filter.py tests/test_load_track.py
git commit -m "feat: cache a sox high-pass filter pass per track to reduce bass distortion"
```

---

### Task 10: Settings modal — restart button visual polish

**Files:**
- Modify: `templates/index.html` (settings modal)
- Modify: `static/css/style.css`
- Modify: `static/js/app.js` (`shutdown-btn` handler)

**Interfaces:**
- Consumes: existing `/api/shutdown` route (no backend change in this task).
- Produces: no new JS/CSS interfaces consumed elsewhere — this task is self-contained UI polish.

- [ ] **Step 1: Restructure the restart button markup into a "danger zone"**

In `templates/index.html`, find:
```html
        <div class="settings-divider"></div>

        <button class="settings-shutdown-btn" id="shutdown-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M18.36 6.64A9 9 0 1 1 5.64 6.64"/>
            <line x1="12" y1="2" x2="12" y2="12"/>
          </svg>
          Reiniciar Eco Records
        </button>

        <p class="settings-shutdown-hint">El dispositivo se reiniciara solo en unos segundos</p>

      </div>
```

Replace with:
```html
        <div class="settings-danger-zone">
          <button class="settings-shutdown-btn" id="shutdown-btn">
            <span class="btn-spinner" id="shutdown-spinner" hidden></span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" id="shutdown-icon">
              <path d="M18.36 6.64A9 9 0 1 1 5.64 6.64"/>
              <line x1="12" y1="2" x2="12" y2="12"/>
            </svg>
            <span id="shutdown-btn-label">Reiniciar Eco Records</span>
          </button>

          <p class="settings-shutdown-hint">El dispositivo se reiniciará solo en unos segundos</p>
        </div>

      </div>
```

- [ ] **Step 2: Add the danger-zone spacing, spinner, and disabled-modal styles**

In `static/css/style.css`, find:
```css
.settings-shutdown-hint {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  margin-top: 4px;
}
```

Insert immediately after it:
```css
.settings-danger-zone {
  width: 100%;
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.modal-card.is-restarting .settings-item,
.modal-card.is-restarting .settings-divider,
.modal-card.is-restarting #settings-close {
  opacity: 0.35;
  pointer-events: none;
  transition: opacity 0.2s ease;
}

.settings-shutdown-btn:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(139, 32, 32, 0.3);
  border-top-color: #8B2020;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
```

(`@keyframes spin` already exists — reused from the disc-spin animation, no new keyframes needed.)

- [ ] **Step 3: Give the restart button a proper loading/disabled/error cycle in `app.js`**

Find:
```js
document.getElementById('shutdown-btn').addEventListener('click', async () => {
  const btn = document.getElementById('shutdown-btn')
  btn.textContent   = 'Reiniciando...'
  btn.disabled      = true

  try {
    await fetch('/api/shutdown', { method: 'POST' })
    btn.textContent = 'Reiniciando — esperá unos segundos'
    setTimeout(() => {
      document.getElementById('settings-modal').style.display = 'none'
    }, 8000)
  } catch (err) {
    btn.textContent  = 'Error al reiniciar'
    btn.disabled     = false
  }
})
```

Replace with:
```js
document.getElementById('shutdown-btn').addEventListener('click', async () => {
  const modalCard = document.querySelector('#settings-modal .modal-card')
  const btn        = document.getElementById('shutdown-btn')
  const spinner    = document.getElementById('shutdown-spinner')
  const label      = document.getElementById('shutdown-btn-label')

  modalCard.classList.add('is-restarting')
  btn.disabled       = true
  spinner.hidden     = false
  label.textContent  = 'Reiniciando...'

  try {
    await fetch('/api/shutdown', { method: 'POST' })
    label.textContent = 'Reiniciando — esperá unos segundos'
    setTimeout(() => {
      document.getElementById('settings-modal').style.display = 'none'
      modalCard.classList.remove('is-restarting')
    }, 8000)
  } catch (err) {
    modalCard.classList.remove('is-restarting')
    spinner.hidden     = true
    btn.disabled       = false
    label.textContent  = 'Error al reiniciar'
  }
})
```

- [ ] **Step 4: Manual verification in the browser**

Run `python app.py` locally and open the settings modal:
1. Click "Reiniciar Eco Records". Confirm: a spinner appears next to the icon, the label changes to "Reiniciando...", and the Volumen info row + "Cerrar" button visibly dim and stop responding to clicks/taps while the request is in flight.
2. On this dev machine `subprocess.Popen(["sudo", "reboot"])` will fail (no `sudo`/`reboot` on Windows), which exercises the error path — confirm the label switches to "Error al reiniciar", the spinner disappears, and the rest of the modal re-enables (dimming removed, clickable again).
3. The success path (label → "Reiniciando — esperá unos segundos", modal auto-closes after 8s) can only be fully verified on the real Pi, where `sudo reboot` actually runs — do that as a final check after deploying.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/css/style.css static/js/app.js
git commit -m "polish: clearer danger-zone separation, spinner, and disabled state on the restart modal"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1↔testing groundwork; Task 2↔Tarea 1 (volumen); Task 9↔Tarea 2 (filtro); Tasks 3-4↔Tarea 3 (batería); Tasks 5-6↔Tarea 4 (historial); Tasks 7-8↔Tarea 5 (estadísticas); Task 10 + the UI steps folded into Tasks 4/6/8↔Tarea 6 (pulido UI, incluido "aplicar el mismo criterio a los nuevos elementos" — done inline per task rather than as a separate late pass, since each new element was styled to match the existing card/pill/list patterns as it was built).
- **Config.json compatibility:** verified explicitly in Task 3's `test_update_battery_config_preserves_existing_keys`; Tasks 5/7 deliberately use separate files (`history.json`, `stats.json`) instead of touching `config.json`, sidestepping the compatibility risk entirely for those two.
- **Low-battery visual warning (optional in spec):** covered by Task 4's `.battery-indicator.low` style (`< 20%` threshold, matching the spec's "~15-20%" suggestion).
- **Type/name consistency check:** `build_mpg123_command(track_path, volume_factor, skip_frames=None)` (Task 2) is called identically in Tasks 2, 5, 9 wiring steps; `get_filtered_track_path` (Task 9) and `log_history`/`increment_album_stat` (Tasks 5/7) names match between their definition steps and their call-site wiring steps and their test monkeypatches.
