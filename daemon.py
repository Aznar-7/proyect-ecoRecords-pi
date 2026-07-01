#!/usr/bin/env python3
"""

ECO Records - Daemon principal
Loop: detecta tag NFC → identifica album → reproduce música (o simula)
"""

import json
import os
import time
import board
import busio
from adafruit_pn532.i2c import PN532_I2C

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
ALBUMS_PATH = os.path.join(BASE_DIR, "albums")

# Estado global
current_uid = None # UID del disco actualmente puesto
current_album = None

# Config
def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

# NFC
def init_nfc():
    print("[ECO] Inicializando lector NFC...")
    i2c   = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c, debug=False)
    ic, ver, rev, support = pn532.firmware_version
    print(f"[ECO] PN532 listo — firmware v{ver}.{rev}")
    pn532.SAM_configuration()
    return pn532

def uid_to_str(uid):
    """Convierte bytes de UID a string legible: 04:A2:3B:CD"""
    return ":".join([format(b, "02X") for b in uid])

# ── Audio (placeholder hasta que llegue el MAX98357A) ──
def play_album(album_name):
    """
    Por ahora simula la reproducción con prints.
    Cuando llegue el MAX98357A, reemplazamos esto con:
        subprocess.Popen(["mpg123", "-q", track_path])
    """
    album_path = os.path.join(ALBUMS_PATH, album_name)

    if not os.path.exists(album_path):
        print(f"[ECO] ⚠ Carpeta no encontrada: {album_path}")
        return

    tracks = sorted([
        f for f in os.listdir(album_path)
        if f.endswith(('.mp3', '.flac', '.wav', '.ogg'))
    ])

    if not tracks:
        print(f"[ECO] ⚠ No hay pistas en: {album_path}")
        return

    print(f"[ECO] ▶ Reproduciendo álbum: {album_name}")
    for i, track in enumerate(tracks, 1):
        print(f"[ECO]   Pista {i}/{len(tracks)}: {track}")

def stop_playback():
    """
    Por ahora solo imprime.
    Cuando haya audio real, acá matamos el proceso de mpg123.
    """
    print("[ECO] ⏹ Reproducción detenida")

# ── Loop principal ───────────────────────────
def main():
    global current_uid, current_album

    print("[ECO] ══════════════════════════════")
    print("[ECO]  Eco Records — Daemon v1.0")
    print("[ECO] ══════════════════════════════")

    pn532 = init_nfc()

    print("[ECO] Esperando discos...\n")

    while True:
        try:
            uid_bytes = pn532.read_passive_target(timeout=0.5)

            if uid_bytes is not None:
                uid = uid_to_str(uid_bytes)

                # Disco nuevo apoyado
                if uid != current_uid:
                    current_uid = uid
                    print(f"[ECO] Disco detectado — UID: {uid}")

                    # Buscar en config
                    config = read_config()
                    album  = config.get("albums", {}).get(uid)

                    if album:
                        current_album = album
                        play_album(album)
                    else:
                        print(f"[ECO] UID no registrado: {uid}")
                        print(f"[ECO] Tip: agregalo al config.json")
                        current_album = None

            else:
                # No hay tag — si había uno antes, detener
                if current_uid is not None:
                    print(f"[ECO] Disco retirado")
                    stop_playback()
                    current_uid   = None
                    current_album = None

        except Exception as e:
            print(f"[ECO] Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()

