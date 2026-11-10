"""One-click launcher for the BJT DC bias web app.

Double-click ``start.bat`` (or run ``python run.py``) and this module:

1. finds the first free TCP port at or after 5000,
2. waits until Flask is actually listening on that port,
3. opens the default browser at that address,
4. serves the Flask app from ``app.py``.

It contains no circuit equations; all of them stay in ``dc_bias.py``.
"""

import socket
import threading
import time
import webbrowser

HOST = "127.0.0.1"
DEFAULT_PORT = 5000
MAX_ATTEMPTS = 20
BROWSER_POLL_INTERVAL = 0.25
BROWSER_TIMEOUT = 15.0


def pick_port(
    host: str = HOST,
    preferred: int = DEFAULT_PORT,
    attempts: int = MAX_ATTEMPTS,
) -> int:
    """Return the first free TCP port at or after ``preferred``.

    Raises ``RuntimeError`` when every port in the scanned range is taken.

    Note: ``SO_REUSEADDR`` is deliberately *not* set. On Windows it lets a
    socket bind to a port that is already in use, which would make this
    check report a busy port as free.
    """
    for offset in range(attempts):
        port = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port

    last = preferred + attempts - 1
    raise RuntimeError(
        f"ไม่พบ port ว่างในช่วง {preferred}-{last} "
        "กรุณาปิดโปรแกรมที่ใช้ port เหล่านี้แล้วลองใหม่"
    )


def port_accepting_connections(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True when something is already listening on ``host:port``."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_server(host: str, port: int, timeout: float = BROWSER_TIMEOUT) -> bool:
    """Poll until Flask is listening on ``host:port`` or ``timeout`` elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_accepting_connections(host, port, timeout=0.5):
            return True
        time.sleep(BROWSER_POLL_INTERVAL)
    return False


def open_browser_when_ready(url: str, host: str, port: int) -> threading.Thread:
    """Start a daemon thread that opens ``url`` once Flask is listening."""

    def _opener() -> None:
        if wait_for_server(host, port):
            webbrowser.open(url)

    thread = threading.Thread(target=_opener, daemon=True)
    thread.start()
    return thread


def main() -> int:
    """Start the web app and open a browser tab. Returns a process exit code."""
    try:
        from app import app
    except ImportError as exc:
        print(f"[ผิดพลาด] โหลดแอปไม่สำเร็จ: {exc}")
        print("วิธีแก้: .venv\\Scripts\\python.exe -m pip install -r requirements.txt")
        return 1

    try:
        port = pick_port()
    except RuntimeError as exc:
        print(f"[ผิดพลาด] {exc}")
        return 1

    url = f"http://{HOST}:{port}/"
    print("=" * 54)
    print("  BJT DC Bias — กำลังเปิดเว็บ...")
    print(f"  {url}")
    print("  ปิดหน้าต่างนี้ = หยุดเว็บ")
    print("=" * 54)

    open_browser_when_ready(url, HOST, port)
    app.run(host=HOST, port=port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
