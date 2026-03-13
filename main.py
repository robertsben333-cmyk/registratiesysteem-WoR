import os
import socket
import threading
import webbrowser
import time
from app import create_app

PORT = 5050
PING_TIMEOUT = 20  # seconds without ping → shutdown


def _port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")


def _watchdog(flask_app):
    """Shut down when the browser has been closed for PING_TIMEOUT seconds."""
    time.sleep(PING_TIMEOUT + 10)  # grace period on startup
    while True:
        time.sleep(3)
        if time.time() - flask_app.config.get("LAST_PING", 0) > PING_TIMEOUT:
            os._exit(0)


app = create_app()

if __name__ == "__main__":
    if _port_in_use(PORT):
        # Already running — open browser to existing instance
        webbrowser.open(f"http://localhost:{PORT}")
    else:
        app.config["LAST_PING"] = time.time()
        threading.Thread(target=open_browser, daemon=True).start()
        threading.Thread(target=_watchdog, args=(app,), daemon=True).start()
        app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
