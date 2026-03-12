import threading
import webbrowser
import time
from app import create_app

PORT = 5050


def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")


app = create_app()

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
