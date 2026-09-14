#!/usr/bin/env python3
"""
ECO Records — Daemon principal v4.2
NFC identifica el disco y reproduce directo (Hall desactivado temporalmente).
Audio real via subprocess limpio por pista, motor sincronizado.
"""

import json
import os
import time
import subprocess
import threading
import board
import busio
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
from mutagen.mp3 import MP3
from ina219 import INA219

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")

MISS_THRESHOLD = 15

MOTOR_PINS  = [5, 6, 13, 26]
MOTOR_DELAY = 0.002

BATTERY_POLL_INTERVAL = 7  # segundos
BATTERY_VOLTAGE_EMPTY = 3.0
BATTERY_VOLTAGE_FULL  = 4.2

current_uid       = None
current_album     = None
current_tracks    = []
current_index     = 0
current_process   = None
play_session      = 0

track_start_time     = 0
accumulated_elapsed  = 0
is_paused            = True
current_duration     = 0
track_started         = False

motor_thread   = None
motor_running  = False

lock = threading.Lock()

# ── Config ───────────────────────────────────
def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def write_full_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def write_state(album, track_index, track_name, total, playing, elapsed=0, duration=0):
    config = read_config()
    config["now_playing"] = {
        "album": album, "track": track_index,
        "track_name": track_name, "total": total, "playing": playing,
        "elapsed": elapsed, "duration": duration
    }
    write_full_config(config)

def read_command():
    config = read_config()
    return config.get("command")

def clear_command():
    config = read_config()
    config["command"] = None
    write_full_config(config)

def get_volume_scale_factor():
    """Convierte el volumen guardado en config.json (0-100) al factor de
    escala que espera mpg123 (-f), donde 32768 = 100%."""
    config = read_config()
    volume_pct = config.get("volume", 70)
    return int((volume_pct / 100) * 32768)

# ── NFC ──────────────────────────────────────
def init_nfc():
    print("[ECO] Inicializando lector NFC...")
    while True:
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            pn532 = PN532_I2C(i2c, debug=False)
            ic, ver, rev, support = pn532.firmware_version
            print(f"[ECO] PN532 listo — firmware v{ver}.{rev}")
            pn532.SAM_configuration()
            return pn532
        except Exception as e:
            print(f"[ECO] PN532 no responde: {e} — reintentando en 5s")
            time.sleep(5)

def uid_to_str(uid):
    return ":".join([format(b, "02X") for b in uid])

# ── Motor ─────────────────────────────────────
def init_motor():
    GPIO.setmode(GPIO.BCM)
    for p in MOTOR_PINS:
        GPIO.setup(p, GPIO.OUT)
    print("[ECO] Motor inicializado")

def _motor_loop():
    global motor_running
    secuencia_full = [
        [0,0,1,1],
        [0,1,1,0],
        [1,1,0,0],
        [1,0,0,1]
    ]
    i = 0
    while motor_running:
        paso = secuencia_full[i % 4]
        for pin, val in zip(MOTOR_PINS, paso):
            GPIO.output(pin, val)
        time.sleep(MOTOR_DELAY)
        i += 1
    for pin in MOTOR_PINS:
        GPIO.output(pin, 0)

def start_motor():
    global motor_thread, motor_running
    if motor_running:
        return
    motor_running = True
    motor_thread = threading.Thread(target=_motor_loop, daemon=True)
    motor_thread.start()
    print("[ECO] Motor: girando")

def stop_motor():
    global motor_running
    if not motor_running:
        return
    motor_running = False
    print("[ECO] Motor: detenido")

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

# ── Pistas ───────────────────────────────────
def get_tracks(album_name):
    album_path = os.path.join(ALBUMS_PATH, album_name)
    if not os.path.exists(album_path):
        return []
    return sorted([
        f for f in os.listdir(album_path)
        if f.endswith(('.mp3', '.flac', '.wav', '.ogg'))
    ])

def clean_track_name(filename):
    name = os.path.splitext(filename)[0]
    name = name.lstrip('0123456789').lstrip(' .-_')
    if ' - ' in name:
        name = name.split(' - ', 1)[1]
    return name.strip()

def get_duration(track_path):
    try:
        return int(MP3(track_path).info.length)
    except Exception as e:
        print(f"[ECO] No se pudo leer duracion: {e}")
        return 0

# ── Control de audio (proceso limpio por pista) ──
def build_mpg123_command(track_path, volume_factor, skip_frames=None):
    """Arma el comando de mpg123 aplicando el volumen actual y, si se pasa
    skip_frames, arrancando desde ese punto (usado al reanudar)."""
    cmd = ["mpg123", "-q", "-f", str(volume_factor)]
    if skip_frames is not None:
        cmd += ["-k", str(skip_frames)]
    cmd += ["--audiodevice", "plughw:0,0", track_path]
    return cmd

def kill_current_process():
    global current_process
    if current_process and current_process.poll() is None:
        try:
            current_process.terminate()
            current_process.wait(timeout=1)
        except Exception:
            try:
                current_process.kill()
            except Exception:
                pass
    current_process = None

def watch_process(proc, session):
    proc.wait()
    with lock:
        if session == play_session and current_process is proc:
            if proc.returncode == 0:
                print("[ECO] Pista terminada, avanzando...")
                _next_track_locked()
            else:
                print(f"[ECO] Proceso terminó con error (rc={proc.returncode}), no avanzando")

def load_track(index):
    global current_index, track_start_time, accumulated_elapsed
    global is_paused, current_duration, current_process, play_session, track_started

    if not current_tracks or index < 0 or index >= len(current_tracks):
        return

    kill_current_process()
    play_session += 1
    session = play_session

    current_index = index
    track_path = os.path.join(ALBUMS_PATH, current_album, current_tracks[index])

    current_duration    = get_duration(track_path)
    track_start_time    = time.time()
    accumulated_elapsed = 0
    is_paused            = False
    track_started         = True

    volume_factor = get_volume_scale_factor()
    current_process = subprocess.Popen(
        build_mpg123_command(track_path, volume_factor),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    t = threading.Thread(target=watch_process, args=(current_process, session), daemon=True)
    t.start()

    track_name = clean_track_name(current_tracks[index])
    print(f"[ECO] Reproduciendo: {track_name} ({current_duration}s)")
    write_state(current_album, index + 1, track_name, len(current_tracks), True, 0, current_duration)

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

def stop_playback():
    global current_album, current_tracks, current_index, play_session, is_paused, track_started
    stop_motor()
    play_session += 1
    kill_current_process()
    current_album  = None
    current_tracks = []
    current_index  = 0
    is_paused      = True
    track_started    = False
    print("[ECO] Disco retirado — reproducción detenida")
    write_state(None, 0, None, 0, False, 0, 0)

def _pause_now():
    global track_start_time, accumulated_elapsed, is_paused, play_session
    if current_process is None or is_paused:
        return
    accumulated_elapsed += time.time() - track_start_time
    is_paused = True
    play_session += 1
    kill_current_process()
    stop_motor()
    track_name = clean_track_name(current_tracks[current_index]) if current_tracks else None
    print(f"[ECO] Pausado en {accumulated_elapsed:.1f}s")
    write_state(current_album, current_index + 1, track_name,
                len(current_tracks), False, accumulated_elapsed, current_duration)

def _resume_now():
    global track_start_time, is_paused, current_process, play_session
    if not is_paused or not current_tracks:
        return
    is_paused = False
    resume_at = accumulated_elapsed
    track_start_time = time.time() - resume_at

    play_session += 1
    session = play_session
    track_path = os.path.join(ALBUMS_PATH, current_album, current_tracks[current_index])
    skip_frames = int(resume_at * 38)

    volume_factor = get_volume_scale_factor()
    current_process = subprocess.Popen(
        build_mpg123_command(track_path, volume_factor, skip_frames=skip_frames),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    t = threading.Thread(target=watch_process, args=(current_process, session), daemon=True)
    t.start()
    start_motor()

    track_name = clean_track_name(current_tracks[current_index])
    print(f"[ECO] Reanudado desde {resume_at:.1f}s")
    write_state(current_album, current_index + 1, track_name,
                len(current_tracks), True, resume_at, current_duration)

def toggle_pause():
    with lock:
        if is_paused:
            if not current_tracks:
                return
            if not track_started:
                load_track(current_index)
                start_motor()
            else:
                _resume_now()
        else:
            _pause_now()

def _next_track_locked():
    if current_tracks and current_index < len(current_tracks) - 1:
        load_track(current_index + 1)
        start_motor()
    else:
        print("[ECO] Fin del album")
        _pause_now()

def next_track():
    with lock:
        if current_tracks and current_index < len(current_tracks) - 1:
            load_track(current_index + 1)
            if not is_paused:
                start_motor()
        else:
            print("[ECO] Ya es la ultima pista")

def prev_track():
    with lock:
        if current_tracks and current_index > 0:
            load_track(current_index - 1)
            if not is_paused:
                start_motor()
        else:
            print("[ECO] Ya es la primera pista")

# ── Procesar comandos de la webapp ───────────
def handle_commands():
    cmd = read_command()
    if not cmd:
        return
    print(f"[ECO] Comando recibido: {cmd}")
    if cmd == "pause":
        toggle_pause()
    elif cmd == "next":
        next_track()
    elif cmd == "prev":
        prev_track()
    clear_command()

# ── Ticker de progreso ────────────────────────
def progress_ticker():
    last_written = -1
    while True:
        try:
            if current_album and not is_paused and current_tracks:
                elapsed = int(accumulated_elapsed + (time.time() - track_start_time))
                if elapsed != last_written:
                    last_written = elapsed
                    track_name = clean_track_name(current_tracks[current_index])
                    write_state(
                        current_album, current_index + 1, track_name,
                        len(current_tracks), True, elapsed, current_duration
                    )
        except Exception:
            pass
        time.sleep(1)

# ── Loop principal ────────────────────────────
def main():
    global current_uid

    print("[ECO] ══════════════════════════════")
    print("[ECO]  Eco Records — Daemon v4.2 (sin Hall)")
    print("[ECO] ══════════════════════════════")

    pn532 = init_nfc()
    init_motor()
    write_state(None, 0, None, 0, False, 0, 0)

    ticker = threading.Thread(target=progress_ticker, daemon=True)
    ticker.start()

    ina = init_battery()
    update_battery_config(ina)  # primer valor disponible de inmediato, sin esperar al primer tick
    battery_thread = threading.Thread(target=battery_ticker, args=(ina,), daemon=True)
    battery_thread.start()

    print("[ECO] Esperando discos...\n")

    miss_count = 0

    while True:
        try:
            handle_commands()

            uid_bytes = pn532.read_passive_target(timeout=0.3)

            if uid_bytes is not None:
                miss_count = 0
                uid = uid_to_str(uid_bytes)
                if uid != current_uid:
                    current_uid = uid
                    print(f"[ECO] Disco detectado — UID: {uid}")
                    config = read_config()
                    album  = config.get("albums", {}).get(uid)
                    if album:
                        with lock:
                            play_album(album)
                    else:
                        print(f"[ECO] UID no registrado: {uid}")
                        config["pending_uid"] = uid
                        write_full_config(config)
            else:
                if current_uid is not None:
                    miss_count += 1
                    if miss_count >= MISS_THRESHOLD:
                        print("[ECO] Disco retirado")
                        with lock:
                            stop_playback()
                        current_uid = None
                        miss_count = 0

            time.sleep(0.15)

        except Exception as e:
            print(f"[ECO] Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ECO] Apagando daemon...")
        stop_motor()
        kill_current_process()
        write_state(None, 0, None, 0, False, 0, 0)
        GPIO.cleanup()
        print("[ECO] Hasta luego.")
