from flask import Flask, jsonify, request, render_template
import json
import os

app = Flask(__name__)

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
        "albums":       list(config.get("albums", {}).values())
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
        # Limpiar nombre: sacar extensión y número de pista
        name = os.path.splitext(t)[0]
        name = name.lstrip('0123456789.- ')
        result.append({ "name": name, "filename": t, "duration": None })
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
