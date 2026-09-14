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
        self.firmware_version = (1, 6, 28, 7)

    def SAM_configuration(self):
        pass

    def read_passive_target(self, timeout=None):
        return None


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


class _FakeAudioInfo:
    def __init__(self):
        self.length = 180


class _FakeMP3:
    def __init__(self, *a, **k):
        self.info = _FakeAudioInfo()


_mutagen_mp3 = _stub_module("mutagen.mp3", MP3=_FakeMP3)
_stub_module("mutagen", mp3=_mutagen_mp3)

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
