#!/usr/bin/env python3
"""
ECO Records — Daemon principal v2.0
NFC + control de audio real vía mpg123
"""

import json
import os
import time
import subprocess
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")

current_uid     = None
current_album   = None
current_tracks  = []
current_index   = 0
mpg123_proc     = None

# ── Config ───────────────────────────────────
def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def write_full_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def write_state(album, track_index, track_name, total, playing):
    config = read_config()
    config["now_playing"] = {
        "album": album, "track": track_index,
        "track_name": track_name, "total": total, "playing": playing
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

# ── Control de mpg123 (modo remoto) ──────────
def start_mpg123():
    global mpg123_proc
    mpg123_proc = subprocess.Popen(
        ["mpg123", "-R", "--audiodevice", "plughw:0,0"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, bufsize=1
    )
    print("[ECO] mpg123 iniciado en modo remoto")

def mpg123_send(cmd):
    if mpg123_proc and mpg123_proc.stdin:
        try:
            mpg123_proc.stdin.write(cmd + "\n")
            mpg123_proc.stdin.flush()
        except Exception as e:
            print(f"[ECO] Error enviando comando a mpg123: {e}")

def load_track(index):
    global current_index
    if not current_tracks or index < 0 or index >= len(current_tracks):
        return
    current_index = index
    track_path = os.path.join(ALBUMS_PATH, current_album, current_tracks[index])
    mpg123_send(f"LOAD {track_path}")
    track_name = clean_track_name(current_tracks[index])
    print(f"[ECO] Reproduciendo: {track_name}")
    write_state(current_album, index + 1, track_name, len(current_tracks), True)

def play_album(album_name):
    global current_album, current_tracks, current_index
    tracks = get_tracks(album_name)
    if not tracks:
        print(f"[ECO] Sin pistas en: {album_name}")
        write_state(album_name, 0, None, 0, False)
        return
    current_album  = album_name
    current_tracks = tracks
    current_index  = 0
    if mpg123_proc is None:
        start_mpg123()
    load_track(0)

def stop_playback():
    global current_album, current_tracks, current_index
    mpg123_send("STOP")
    current_album  = None
    current_tracks = []
    current_index  = 0
    print("[ECO] Reproducción detenida")
    write_state(None, 0, None, 0, False)

def toggle_pause():
    mpg123_send("PAUSE")

def next_track():
    if current_tracks and current_index < len(current_tracks) - 1:
        load_track(current_index + 1)

def prev_track():
    if current_tracks and current_index > 0:
        load_track(current_index - 1)

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

# ── Loop principal ────────────────────────────
def main():
    global current_uid, current_album

    print("[ECO] ══════════════════════════════")
    print("[ECO]  Eco Records — Daemon v2.0")
    print("[ECO] ══════════════════════════════")

    pn532 = init_nfc()
    write_state(None, 0, None, 0, False)
    print("[ECO] Esperando discos...\n")

    while True:
        try:
            handle_commands()

            uid_bytes = pn532.read_passive_target(timeout=0.3)

            if uid_bytes is not None:
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
                    print("[ECO] Disco retirado")
                    stop_playback()
                    current_uid = None

            time.sleep(0.2)

        except Exception as e:
            print(f"[ECO] Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[ECO] Apagando daemon...")
        if mpg123_proc:
            mpg123_send("QUIT")
        write_state(None, 0, None, 0, False)
        print("[ECO] Hasta luego.")
