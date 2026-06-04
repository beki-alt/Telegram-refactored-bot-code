"""
keep_alive.py
─────────────
Lightweight Flask web server for Replit keep-alive and health checks.
Runs in a daemon background thread so it doesn't block the event loop.
"""

import os
import time
import threading
import logging
from flask import Flask, jsonify

logger = logging.getLogger(__name__)

_app = Flask(__name__)
_start_time: float = 0.0


@_app.route("/")
def home():
    return jsonify({"status": "alive", "service": "Telegram Payment Bot"})


@_app.route("/health")
def health():
    uptime = int(time.time() - _start_time) if _start_time else 0
    return jsonify({"status": "ok", "uptime_seconds": uptime})


@_app.route("/ping")
def ping():
    return "pong", 200


def _run_flask():
    global _start_time
    _start_time = time.time()
    # Use PORT from env (Replit assigns this), fallback to 8080
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Keep-alive Flask server starting on port {port}")
    _app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def keep_alive():
    """Start the Flask keep-alive server in a daemon background thread."""
    thread = threading.Thread(target=_run_flask, daemon=True, name="KeepAlive")
    thread.start()
    logger.info("Keep-alive server started.")
