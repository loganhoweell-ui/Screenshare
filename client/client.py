import sys
import time
import threading
from io import BytesIO

import mss
from PIL import Image
import websocket

# ── CONFIG ─────────────────────────────────────────────────────────────────────
SERVER_URL = "ws://YOUR_SERVER_URL"   # e.g. ws://myapp.railway.app
SECRET     = "changeme"
TARGET_FPS = 30
QUALITY    = 60        # JPEG quality 1-95
WIDTH      = 1920
HEIGHT     = 1080
MONITOR    = 1         # 1 = primary monitor
# ───────────────────────────────────────────────────────────────────────────────

_stop = threading.Event()


def capture_loop(ws):
    with mss.mss() as sct:
        monitor = sct.monitors[MONITOR]
        interval = 1.0 / TARGET_FPS
        print(f"Streaming {WIDTH}x{HEIGHT} @ {TARGET_FPS}fps  quality={QUALITY}")

        while not _stop.is_set():
            t0 = time.perf_counter()
            try:
                shot = sct.grab(monitor)
                img = Image.frombytes("RGB", (shot.width, shot.height), shot.bgra, "raw", "BGRX")

                if img.width != WIDTH or img.height != HEIGHT:
                    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)

                buf = BytesIO()
                img.save(buf, format="JPEG", quality=QUALITY, optimize=False)
                # Send raw binary bytes — no base64 overhead
                ws.send_binary(buf.getvalue())

            except Exception as e:
                print(f"[capture] {e}")
                _stop.set()
                break

            elapsed = time.perf_counter() - t0
            wait = interval - elapsed
            if wait > 0:
                time.sleep(wait)


def on_open(ws):
    print("[ws] Connected — starting capture")
    _stop.clear()
    threading.Thread(target=capture_loop, args=(ws,), daemon=True).start()


def on_error(ws, error):
    print(f"[ws] Error: {error}")


def on_close(ws, code, msg):
    _stop.set()
    print(f"[ws] Closed: {code} {msg}")


def main():
    if SERVER_URL == "ws://YOUR_SERVER_URL":
        print("ERROR: Set SERVER_URL in client.py before running.")
        sys.exit(1)

    url = f"{SERVER_URL}?role=broadcaster&secret={SECRET}"
    while True:
        print(f"[ws] Connecting to {SERVER_URL} ...")
        ws = websocket.WebSocketApp(url, on_open=on_open, on_error=on_error, on_close=on_close)
        ws.run_forever(ping_interval=20, ping_timeout=10)
        print("[ws] Reconnecting in 3s...")
        time.sleep(3)


if __name__ == "__main__":
    main()
