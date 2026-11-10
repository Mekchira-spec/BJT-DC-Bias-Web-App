"""Tests for the one-click launcher (no server is started)."""

import socket
import threading
import unittest
from unittest import mock

import run


class TestPickPort(unittest.TestCase):
    def test_returns_preferred_when_free(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free = probe.getsockname()[1]
        self.assertEqual(run.pick_port(preferred=free, attempts=1), free)

    def test_skips_busy_port(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            chosen = run.pick_port(preferred=taken, attempts=5)
            self.assertNotEqual(chosen, taken)
            self.assertGreater(chosen, taken)

    def test_raises_when_no_port_available(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            taken = busy.getsockname()[1]
            with self.assertRaises(RuntimeError):
                run.pick_port(preferred=taken, attempts=1)


class TestPortAcceptingConnections(unittest.TestCase):
    def test_true_when_listening(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertTrue(run.port_accepting_connections("127.0.0.1", port))

    def test_false_when_nothing_listening(self):
        self.assertFalse(run.port_accepting_connections("127.0.0.1", 1))


class TestWaitForServer(unittest.TestCase):
    def test_returns_true_when_server_is_listening(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            self.assertTrue(run.wait_for_server("127.0.0.1", port, timeout=2.0))

    def test_returns_false_when_nothing_ever_listens(self):
        with socket.socket() as blocker:
            blocker.bind(("127.0.0.1", 0))
            blocker.listen(1)
            taken = blocker.getsockname()[1]
        # blocker closed here; nothing listens on that port anymore.
        self.assertFalse(run.wait_for_server("127.0.0.1", taken, timeout=0.3))


class TestOpenBrowserWhenReady(unittest.TestCase):
    def test_opens_browser_when_port_is_listening(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            # listener is still open here so the poller will find it
            with mock.patch.object(run.webbrowser, "open") as fake_open:
                thread = run.open_browser_when_ready(
                    f"http://127.0.0.1:{port}/", "127.0.0.1", port
                )
                thread.join(2.0)
                fake_open.assert_called_once_with(f"http://127.0.0.1:{port}/")


if __name__ == "__main__":
    unittest.main()
