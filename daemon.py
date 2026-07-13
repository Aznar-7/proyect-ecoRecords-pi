#!/usr/bin/env python3
"""
ECO Records — Daemon principal v3.1
NFC + audio real via subprocess limpio por pista + motor
"""

import json
import os
import time
import subprocess
import signal
import threading
import board
import busio
import RPi.GPIO as GPIO
from adafruit_pn532.i2c import PN532_I2C
from mutagen.mp3 import MP3

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")

MISS_THRESHOLD = 5

MOTOR_PINS  = [5, 6, 13, 26]
MOTOR_DELAY = 0.002

current_uid       = None
current_album     = None
current_tracks    = []
current_index     = 0
current_process   = None
play_session      = 0

track_start_time     = 0
accumulated_elapsed  = 0
is_paused            = False
current_duration     = 0

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
        [1,0,0,1],
        [1,1,0,0],
        [0,1,1,0],
        [0,0,1,1],
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
    print(f"[ECO] Proceso terminó con returncode: {proc.returncode}")
    with lock:
        if session == play_session and current_process is proc:
            if proc.returncode == 0:
                print("[ECO] Pista terminada normalmente, avanzando...")
                _next_track_locked()
            else:
                print("[ECO] Proceso terminó con error, NO avanzando")

def load_track(index):
    global current_index, track_start_time, accumulated_elapsed
    global is_paused, current_duration, current_process, play_session

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

    current_process = subprocess.Popen(
        ["mpg123", "-q", "--audiodevice", "plughw:0,0", track_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    t = threading.Thread(target=watch_process, args=(current_process, session), daemon=True)
    t.start()

    track_name = clean_track_name(current_tracks[index])
    print(f"[ECO] Reproduciendo: {track_name} ({current_duration}s)")
    start_motor()
    write_state(current_album, index + 1, track_name, len(current_tracks), True, 0, current_duration)

def play_album(album_name):
    global current_album, current_tracks, current_index
    tracks = get_tracks(album_name)
    if not tracks:
        print(f"[ECO] Sin pistas en: {album_name}")
        write_state(album_name, 0, None, 0, False)
        return
    with lock:
        current_album  = album_name
        current_tracks = tracks
        current_index  = 0
        load_track(0)

def stop_playback():
    global current_album, current_tracks, current_index, play_session
    stop_motor()
    play_session += 1
    kill_current_process()
    current_album  = None
    current_tracks = []
    current_index  = 0
    print("[ECO] Reproducción detenida")
    write_state(None, 0, None, 0, False, 0, 0)

def toggle_pause():
    global track_start_time, accumulated_elapsed, is_paused, play_session
    with lock:
        if not current_process and not is_paused:
            return

        if not is_paused:
            accumulated_elapsed += time.time() - track_start_time
            is_paused = True
            play_session += 1
            kill_current_process()
            stop_motor()
            print(f"[ECO] Pausado en {accumulated_elapsed:.1f}s")
        else:
            is_paused = False
            resume_at = accumulated_elapsed
            track_start_time = time.time() - resume_at
            _relaunch_from(resume_at)
            start_motor()
            print(f"[ECO] Reanudado desde {resume_at:.1f}s")

def _relaunch_from(seconds):
    global current_process, play_session
    play_session += 1
    session = play_session

    track_path = os.path.join(ALBUMS_PATH, current_album, current_tracks[current_index])
    skip_frames = int(seconds * 38)

    current_process = subprocess.Popen(
        ["mpg123", "-q", "-k", str(skip_frames), "--audiodevice", "plughw:0,0", track_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    t = threading.Thread(target=watch_process, args=(current_process, session), daemon=True)
    t.start()

def _next_track_locked():
    if current_tracks and current_index < len(current_tracks) - 1:
        load_track(current_index + 1)
    else:
        print("[ECO] Fin del album")
        stop_playback()

def next_track():
    with lock:
        if current_tracks and current_index < len(current_tracks) - 1:
            load_track(current_index + 1)
        else:
            print("[ECO] Ya es la ultima pista")

def prev_track():
    with lock:
        if current_tracks and current_index > 0:
            load_track(current_index - 1)
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
    print("[ECO]  Eco Records — Daemon v3.1")
    print("[ECO] ══════════════════════════════")

    pn532 = init_nfc()
    init_motor()
    write_state(None, 0, None, 0, False, 0, 0)

    ticker = threading.Thread(target=progress_ticker, daemon=True)
    ticker.start()

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
