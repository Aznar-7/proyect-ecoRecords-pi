#!/usr/bin/env python3
"""
ECO Records — Daemon principal v1.2
Detecta disco NFC → identifica álbum → reporta canción actual
"""

import json
import os
import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

# ── Rutas ────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")

# ── Estado global ────────────────────────────
current_uid   = None
current_album = None
current_track = 0

# ── Config ───────────────────────────────────
def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def write_state(album, track_index, track_name, total, playing):
    """
    Escribe el estado completo en config.json.
    track_index → número de pista (1-based)
    track_name  → nombre legible de la canción actual
    """
    config = read_config()
    config["now_playing"] = {
        "album":      album,
        "track":      track_index,
        "track_name": track_name,
        "total":      total,
        "playing":    playing
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

# ── Pistas ───────────────────────────────────
def get_tracks(album_name):
    """Devuelve lista ordenada de pistas del álbum"""
    album_path = os.path.join(ALBUMS_PATH, album_name)
    if not os.path.exists(album_path):
        return []
    return sorted([
        f for f in os.listdir(album_path)
        if f.endswith(('.mp3', '.flac', '.wav', '.ogg'))
    ])

def clean_track_name(filename):
    """
    Convierte '01 - Billie Jean.mp3' → 'Billie Jean'
    Saca número de pista, guiones y extensión
    """
    name = os.path.splitext(filename)[0]  # sacar extensión
    name = name.lstrip('0123456789')       # sacar número inicial
    name = name.lstrip(' .-_')            # sacar separadores
    return name.strip()

# ── Reproducción ─────────────────────────────
def play_album(album_name):
    global current_track

    tracks = get_tracks(album_name)
    if not tracks:
        print(f"[ECO] ⚠ No hay pistas en: {album_name}")
        write_state(album_name, 0, None, 0, False)
        return

    total      = len(tracks)
    current_track = 1
    track_name = clean_track_name(tracks[0])  # primera pista

    album_display = album_name.replace("-", " ").replace("_", " ").title()
    print(f"[ECO] ▶ {track_name} — {album_display}")

    write_state(album_name, 1, track_name, total, True)

    # Debug: mostrar todas las pistas
    for i, t in enumerate(tracks, 1):
        print(f"[ECO]   {i}/{total}: {clean_track_name(t)}")

    # Cuando llegue el MAX98357A, acá va el subprocess de mpg123

def stop_playback():
    global current_track
    current_track = 0
    print("[ECO] ⏹ Reproducción detenida")
    write_state(None, 0, None, 0, False)

# ── Loop principal ────────────────────────────
def main():
    global current_uid, current_album

    print("[ECO] ══════════════════════════════")
    print("[ECO]  Eco Records — Daemon v1.2")
    print("[ECO] ══════════════════════════════")

    pn532 = init_nfc()
    write_state(None, 0, None, 0, False)

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
                        write_state(None, 0, None, 0, False)
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
