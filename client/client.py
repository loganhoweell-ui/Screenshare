import sys
import time
import json
import threading
from io import BytesIO

import mss
from PIL import Image
import websocket
import pyautogui

# ── CONFIG ─────────────────────────────────────────────────────────────────────
SERVER_URL = "wss://abundant-presence-production-7b11.up.railway.app"
SECRET     = "changeme"
TARGET_FPS = 30
QUALITY    = 60
WIDTH      = 1920
HEIGHT     = 1080
MONITOR    = 1
# ───────────────────────────────────────────────────────────────────────────────

pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

_stop = threading.Event()

SCREEN_W, SCREEN_H = pyautogui.size()

KEY_MAP = {
    'Enter': 'enter', 'Backspace': 'backspace', 'Tab': 'tab',
    'Escape': 'esc', 'Delete': 'delete', 'Insert': 'insert',
    'Home': 'home', 'End': 'end', 'PageUp': 'pageup', 'PageDown': 'pagedown',
    'ArrowLeft': 'left', 'ArrowRight': 'right', 'ArrowUp': 'up', 'ArrowDown': 'down',
    'Control': 'ctrl', 'Shift': 'shift', 'Alt': 'alt', 'Meta': 'winleft',
    'CapsLock': 'capslock', ' ': 'space',
    'F1':'f1','F2':'f2','F3':'f3','F4':'f4','F5':'f5','F6':'f6',
    'F7':'f7','F8':'f8','F9':'f9','F10':'f10','F11':'f11','F12':'f12',
}

def map_key(key):
    if key in KEY_MAP:
        return KEY_MAP[key]
    if len(key) == 1:
        return key
    return None


def handle_input(event):
    t = event.get('type')
    try:
        if t == 'mousemove':
            x = int(event['x'] * SCREEN_W)
            y = int(event['y'] * SCREEN_H)
            pyautogui.moveTo(x, y)

        elif t == 'mousedown':
            x = int(event['x'] * SCREEN_W)
            y = int(event['y'] * SCREEN_H)
            pyautogui.mouseDown(x, y, button=event.get('button', 'left'))

        elif t == 'mouseup':
            x = int(event['x'] * SCREEN_W)
            y = int(event['y'] * SCREEN_H)
            pyautogui.mouseUp(x, y, button=event.get('button', 'left'))

        elif t == 'scroll':
            clicks = -int(event.get('delta', 0) / 100)
            if clicks != 0:
                pyautogui.scroll(clicks)

        elif t == 'keydown':
            key = map_key(event.get('key', ''))
            if key:
                pyautogui.keyDown(key)

        elif t == 'keyup':
            key = map_key(event.get('key', ''))
            if key:
                pyautogui.keyUp(key)

    except Exception as e:
        print(f"[input] {e}")


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
                ws.send(buf.getvalue(), opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                print(f"[capture] {e}")
                _stop.set()
                break

            elapsed = time.perf_counter() - t0
            wait = interval - elapsed
            if wait > 0:
                time.sleep(wait)


def on_open(ws):
    print("[ws] Connected — starting capture + remote control")
    _stop.clear()
    threading.Thread(target=capture_loop, args=(ws,), daemon=True).start()


def on_message(ws, message):
    try:
        event = json.loads(message)
        handle_input(event)
    except Exception as e:
        print(f"[msg] {e}")


def on_error(ws, error):
    print(f"[ws] Error: {error}")


def on_close(ws, code, msg):
    _stop.set()
    print(f"[ws] Closed: {code} {msg}")


def main():
    url = f"{SERVER_URL}?role=broadcaster&secret={SECRET}"
    while True:
        print(f"[ws] Connecting to {SERVER_URL} ...")
        ws = websocket.WebSocketApp(
            url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        ws.run_forever(ping_interval=20, ping_timeout=10)
        print("[ws] Reconnecting in 3s...")
        time.sleep(3)


if __name__ == "__main__":
    main()
