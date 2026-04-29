from flask import Flask, jsonify, request
import json
from pathlib import Path

app = Flask(__name__)
CART = Path("/opt/shipyard/data/endurance/carteira.json")

def load(): return json.loads(CART.read_text()) if CART.exists() else []
def save(d): CART.write_text(json.dumps(d, indent=2, ensure_ascii=False))

@app.route("/api/carteira", methods=["GET"])
def get():
    return jsonify(load())

@app.route("/api/carteira", methods=["POST"])
def post():
    save(request.json); return jsonify({"ok": True})

@app.route("/api/carteira/<ticker>", methods=["DELETE"])
def delete(ticker):
    save([p for p in load() if p["ticker"] != ticker])
    return jsonify({"ok": True})

@app.route("/api/carteira/<ticker>", methods=["PATCH"])
def patch(ticker):
    d = load()
    for p in d:
        if p["ticker"] == ticker:
            p.update(request.json)
    save(d); return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=False)
