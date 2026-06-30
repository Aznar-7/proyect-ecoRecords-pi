from flask import Flask, jsonify, request, render_template
import json
import os

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def read_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def write_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)

# ── Página principal ──────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")

# ── API: estado actual ────────────────────────────────────
@app.route("/api/status")
def status():
    config = read_config()
    return jsonify({
        "playing": "minecraft",
        "track": 3,
        "total_tracks": 8,
        "volume": config["volume"],
        "lights": config["lights"],
        "albums": list(config["albums"].values())
    })

# ── API: cambiar volumen ──────────────────────────────────
@app.route("/api/volume", methods=["POST"])
def set_volume():
    data = request.get_json()
    volume = int(data.get("volume", 70))
    config = read_config()
    config["volume"] = volume
    write_config(config)
    return jsonify({"ok": True, "volume": volume})

# ── API: cambiar luces ────────────────────────────────────
@app.route("/api/lights", methods=["POST"])
def set_lights():
    data = request.get_json()
    preset = data.get("preset", "warm")
    config = read_config()
    config["lights"] = preset
    write_config(config)
    return jsonify({"ok": True, "lights": preset})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
