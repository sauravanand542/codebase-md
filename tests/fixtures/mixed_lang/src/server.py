"""Flask backend server."""

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/api/status")
def status():
    """Return server status."""
    return jsonify({"status": "ok", "version": "0.1.0"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
