#!/usr/bin/env python3
"""
ECO Records — Daemon principal
Loop: detecta tag NFC → identifica álbum → actualiza estado en config.json
"""

import json
import os
import time
import subprocess
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

# ── Rutas ────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")

# ── Estado global ────────────────────────────
current_uid     = None
current_album   = None
current_process = None  # proceso de audio (cuando llegue el MAX98357A)

# ── Config ───────────────────────────────────
def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def write_state(album, track, total, playing):
    """Escribe el estado actual en config.json para que Flask lo lea"""
    config = read_config()
    config["now_playing"] = {
        "album": album,
        "track": track,
        "total": total,
        "playing": playing
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

# ── NFC ──────────────────────────────────────
def init_nfc():
    print("[ECO] Inicializando lector NFC...")
    i2c   = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"[ECO] PN532 listo — firmware v{ver}.{rev}")
    pn532.SAM_configuration()
    return pn532

def uid_to_str(uid):
    return ":".join([format(b, "02X") for b in uid])

# ── Audio ─────────────────────────────────────
def get_tracks(album_name):
    """Devuelve lista ordenada de pistas del álbum"""
    album_path = os.path.join(ALBUMS_PATH, album_name)
    if not os.path.exists(album_path):
        return []
    return sorted([
        f for f in os.listdir(album_path)
        if f.endswith(('.mp3', '.flac', '.wav', '.ogg'))
    ])

def play_album(album_name):
    global current_process
    tracks = get_tracks(album_name)

    if not tracks:
        print(f"[ECO] ⚠ No hay pistas en: {album_name}")
        write_state(album_name, 0, 0, False)
        return

    total = len(tracks)
    print(f"[ECO] ▶ Reproduciendo: {album_name} ({total} pistas)")

    # Actualizar estado — sonando pista 1
    write_state(album_name, 1, total, True)

    # Cuando llegue el MAX98357A, descomentar esto:
    # album_path = os.path.join(ALBUMS_PATH, album_name)
    # track_path = os.path.join(album_path, tracks[0])
    # current_process = subprocess.Popen(["mpg123", "-q", track_path])

    for i, track in enumerate(tracks, 1):
        print(f"[ECO]   Pista {i}/{total}: {track}")

def stop_playback():
    global current_process
    print("[ECO] ⏹ Reproducción detenida")
    write_state(None, 0, 0, False)

    # Cuando llegue el MAX98357A, descomentar esto:
    # if current_process:
    #     current_process.terminate()
    #     current_process = None

# ── Loop principal ────────────────────────────
def main():
    global current_uid, current_album

    print("[ECO] ══════════════════════════════")
    print("[ECO]  Eco Records — Daemon v1.1")
    print("[ECO] ══════════════════════════════")

    pn532 = init_nfc()

    # Resetear estado al arrancar
    write_state(None, 0, 0, False)

    print("[ECO] Esperando discos...\n")

    while True:
        try:
            uid_bytes = pn532.read_passive_target(timeout=0.5)

            if uid_bytes is not None:
                uid = uid_to_str(uid_bytes)

                if uid != current_uid:
                    current_uid = uid
                    print(f"[ECO] Disco detectado — UID: {uid}")

                    config = read_config()
                    album  = config.get("albums", {}).get(uid)

                    if album:
                        current_album = album
                        play_album(album)
                    else:
                        print(f"[ECO] UID no registrado: {uid}")
                        write_state(None, 0, 0, False)
                        current_album = None

            else:
                if current_uid is not None:
                    print("[ECO] Disco retirado")
                    stop_playback()
                    current_uid   = None
                    current_album = None

        except Exception as e:
            print(f"[ECO] Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
