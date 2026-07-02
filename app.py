from flask import Flask, jsonify, request, render_template
import json
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
ALBUMS_PATH = os.path.join(os.path.dirname(__file__), "albums")

def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def write_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)

def reset_now_playing():
    """Resetea el estado de reproducción al arrancar Flask"""
    try:
        config = read_config()
        config["now_playing"] = {
            "album": None,
            "track": 0,
            "track_name": None,
            "total": 0,
            "playing": False
        }
        write_config(config)
    except Exception:
        pass

reset_now_playing()

# ── Página principal ──────────────────────────
@app.route("/")
def home():
    return render_template("index.html")

# ── API: estado actual ────────────────────────
@app.route("/api/status")
def status():
    config     = read_config()
    now        = config.get("now_playing", {})
    album_name = now.get("album")
    track_name = now.get("track_name")

    # Nombre legible del álbum
    display_name = None
    if album_name:
        display_name = album_name.replace("-", " ").replace("_", " ").title()

    return jsonify({
        "playing":      display_name,
        "raw_album":    album_name,
        "track_name":   track_name,
        "track":        now.get("track", 0),
        "total_tracks": now.get("total", 0),
        "is_playing":   now.get("playing", False),
        "volume":       config.get("volume", 70),
        "lights":       config.get("lights", "warm"),
        "albums":       list(config.get("albums", {}).values()),
        "pending_uid":  config.get("pending_uid", None),
    })

# ── API: listar álbumes ───────────────────────
@app.route("/api/albums")
def list_albums():
    albums = []
    if os.path.exists(ALBUMS_PATH):
        for folder in sorted(os.listdir(ALBUMS_PATH)):
            folder_path = os.path.join(ALBUMS_PATH, folder)
            if os.path.isdir(folder_path):
                tracks = [
                    f for f in os.listdir(folder_path)
                    if f.endswith(('.mp3', '.flac', '.wav', '.ogg'))
                ]
                albums.append({
                    "id":     folder,
                    "name":   folder.replace("-", " ").replace("_", " ").title(),
                    "tracks": len(tracks)
                })
    return jsonify(albums)


# ── API: pistas de un álbum ───────────────────
@app.route("/api/albums/<album_id>/tracks")
def list_tracks(album_id):
    album_path = os.path.join(ALBUMS_PATH, album_id)
    if not os.path.exists(album_path):
        return jsonify([])

    tracks = sorted([
        f for f in os.listdir(album_path)
        if f.endswith(('.mp3', '.flac', '.wav', '.ogg'))
    ])

    result = []
    for t in tracks:
        name = os.path.splitext(t)[0]      # sacar extensión
        name = name.lstrip('0123456789')    # sacar número inicial
        name = name.lstrip(' .-_')         # sacar separadores

        # Limpiar el nombre del artista que YouTube agrega
        # "Elvis Presley - Can't Help Falling In Love (Official Video)" → "Can't Help Falling In Love"
        # Patrones comunes: "Artista - Canción", "Artista - Canción (Official Video)", etc.
        if ' - ' in name:
            parts = name.split(' - ', 1)
            # Si la segunda parte parece el título real (más corta o sin "Official"), usarla
            name = parts[1]

        # Limpiar sufijos comunes de YouTube
        for suffix in [
            ' (Official Video)', ' (Official Music Video)', ' (Official Audio)',
            ' (Lyrics)', ' (Lyric Video)', ' (Audio)', ' (HD)',
            ' [Official Video]', ' [Official Audio]', ' [Lyrics]',
            ' (Remastered)', ' (Remastered 2009)', ' (Remastered 2011)',
            ' (Remastered 1999)', ' (2008 Remastered)', ' (4K)',
            ' (4K Remaster)', ' (Official)', ' (Video)',
        ]:
            name = name.replace(suffix, '').replace(suffix.lower(), '')

        # Limpiar paréntesis vacíos que puedan quedar
        import re
        name = re.sub(r'\s*\([^)]*\)\s*$', '', name).strip()

        result.append({
            "name":     name.strip(),
            "filename": t,
            "duration": None
        })

    return jsonify(result)

# ── API: cambiar volumen ──────────────────────
@app.route("/api/volume", methods=["POST"])
def set_volume():
    data   = request.get_json()
    volume = int(data.get("volume", 70))
    config = read_config()
    config["volume"] = volume
    write_config(config)
    return jsonify({"ok": True, "volume": volume})

# ── API: cambiar luces ────────────────────────
@app.route("/api/lights", methods=["POST"])
def set_lights():
    data   = request.get_json()
    preset = data.get("preset", "warm")
    config = read_config()
    config["lights"] = preset
    write_config(config)
    return jsonify({"ok": True, "lights": preset})

# ── API: subir álbum ──────────────────────────
@app.route("/api/upload", methods=["POST"])
def upload_album():
    album_name = request.form.get("album_name", "").strip()
    files      = request.files.getlist("tracks")

    if not album_name:
        return jsonify({"ok": False, "error": "Nombre requerido"}), 400
    if not files:
        return jsonify({"ok": False, "error": "Sin archivos"}), 400

    safe_name  = album_name.lower().replace(" ", "-")
    album_path = os.path.join(ALBUMS_PATH, safe_name)
    os.makedirs(album_path, exist_ok=True)

    saved = []
    for f in files:
        if f.filename.endswith(('.mp3', '.flac', '.wav', '.ogg')):
            f.save(os.path.join(album_path, f.filename))
            saved.append(f.filename)

    return jsonify({
        "ok":           True,
        "album":        safe_name,
        "tracks_saved": len(saved),
        "files":        saved
    })


# ── API: UID pendiente de asociar ─────────────
@app.route("/api/pending")
def get_pending():
    config = read_config()
    return jsonify({
        "uid": config.get("pending_uid", None)
    })

# ── API: asociar UID a álbum ──────────────────
@app.route("/api/learn", methods=["POST"])
def learn_disc():
    data  = request.get_json()
    uid   = data.get("uid")
    album = data.get("album")

    if not uid or not album:
        return jsonify({"ok": False, "error": "Faltan datos"}), 400

    config = read_config()
    config["albums"][uid] = album

    # Limpiar el pending
    config.pop("pending_uid", None)

    write_config(config)
    print(f"[ECO] Disco aprendido: {uid} → {album}")
    return jsonify({"ok": True, "uid": uid, "album": album})

# ── API: descartar UID pendiente ──────────────
@app.route("/api/pending/discard", methods=["POST"])
def discard_pending():
    config = read_config()
    config.pop("pending_uid", None)
    write_config(config)
    return jsonify({"ok": True})


# ── API: apagado seguro ───────────────────────
@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    import subprocess
    write_config_shutdown()
    subprocess.Popen(["sudo", "shutdown", "-h", "now"])
    return jsonify({"ok": True, "message": "Apagando en 5 segundos..."})

def write_config_shutdown():
    """Limpia el estado antes de apagar"""
    try:
        config = read_config()
        config["now_playing"] = {
            "album": None,
            "track": 0,
            "track_name": None,
            "total": 0,
            "playing": False
        }
        write_config(config)
    except Exception:
        pass


# ── Descarga via YouTube ──────────────────────
import subprocess
import threading

download_status = {
    "running": False,
    "progress": 0,
    "message": "",
    "error": None,
    "album": None
}

def run_download(url, album_name):
    global download_status
    safe_name  = album_name.lower().replace(" ", "-")
    album_path = os.path.join(ALBUMS_PATH, safe_name)
    os.makedirs(album_path, exist_ok=True)

    download_status.update({
        "running": True,
        "progress": 0,
        "message": "Iniciando descarga...",
        "error": None,
        "album": safe_name
    })

    try:
        python = os.path.join(BASE_DIR, "venv", "bin", "python3")
        cmd = [
            python ,"-m", "yt_dlp",
            "-x", "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", os.path.join(album_path, "%(playlist_index)02d - %(title)s.%(ext)s"),
            "--newline",
            url
        ]

        print(f"[ECO] Corriendo: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=BASE_DIR
        )

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            # Parsear progreso de yt-dlp
            if "[download]" in line and "%" in line:
                try:
                    pct = float(line.split("%")[0].split()[-1])
                    download_status["progress"] = round(pct)
                    download_status["message"]  = f"Descargando... {round(pct)}%"
                except Exception:
                    pass
            elif "[ExtractAudio]" in line:
                download_status["message"] = "Convirtiendo a MP3..."
            elif "[ffmpeg]" in line:
                download_status["message"] = "Procesando audio..."
            elif "Downloading item" in line:
                download_status["message"] = line
                download_status["progress"] = 0

        process.wait()

        print(f"[ECO] yt-dlp returncode: {process.returncode}")

        if process.returncode == 0:
            download_status.update({
                "running":  False,
                "progress": 100,
                "message":  "¡Listo!",
                "error":    None
            })
        else:
            download_status.update({
                "running": False,
                "message": "Error en la descarga",
                "error":   "yt-dlp terminó con error"
            })

    except Exception as e:
        download_status.update({
            "running": False,
            "message": "Error",
            "error":   str(e)
        })

@app.route("/api/download", methods=["POST"])
def start_download():
    global download_status

    if download_status["running"]:
        return jsonify({"ok": False, "error": "Ya hay una descarga en curso"}), 400

    data       = request.get_json()
    url        = data.get("url", "").strip()
    album_name = data.get("album_name", "").strip()

    if not url:
        return jsonify({"ok": False, "error": "URL requerida"}), 400
    if not album_name:
        return jsonify({"ok": False, "error": "Nombre de álbum requerido"}), 400

    thread = threading.Thread(target=run_download, args=(url, album_name))
    thread.daemon = True
    thread.start()

    return jsonify({"ok": True, "message": "Descarga iniciada"})

@app.route("/api/download/status")
def download_progress():
    return jsonify(download_status)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
