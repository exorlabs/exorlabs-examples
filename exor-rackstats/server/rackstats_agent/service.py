import copy
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
import ssl
import sys
import threading
import time
from urllib.parse import urlsplit


class SnapshotStore:
    def __init__(self, collector, source, interval=5, clock=time.monotonic):
        self.collector, self.source, self.interval, self.clock = collector, source, interval, clock
        self.lock = threading.Lock()
        self.last = None
        self.last_time = None
        self.failed = False
        self.stop = threading.Event()
        self.thread = None

    def refresh(self):
        try:
            sample = self.collector.collect()
            sample["observed_at"] = datetime.now(timezone.utc).isoformat()
            with self.lock:
                self.last, self.last_time, self.failed = sample, self.clock(), False
        except Exception as error:
            with self.lock: self.failed = True
            logging.warning("Collector sample failed (%s)", type(error).__name__)

    def payload(self):
        with self.lock:
            if self.last is None:
                return 503, {"schema_version": 1, "source": self.source, "state": "unavailable", "age_seconds": None,
                             "observed_at": None, "host": None, "vms": [], "warnings": ["collector_unavailable"]}
            age = max(0, self.clock() - self.last_time)
            result = copy.deepcopy(self.last)
            result.update(schema_version=1, source=self.source, age_seconds=round(age, 2),
                          state="stale" if self.failed or age > max(15, self.interval * 3) else "fresh")
            return 200, result

    def start(self):
        self.refresh()
        def worker():
            while not self.stop.wait(self.interval): self.refresh()
        self.thread = threading.Thread(target=worker, name="collector", daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread: self.thread.join(timeout=15)


class StatsHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]
        if isinstance(error, (ssl.SSLError, ConnectionError, TimeoutError)):
            logging.debug("Client connection closed (%s)", type(error).__name__)
            return
        super().handle_error(request, client_address)


def make_server(store, token, host="127.0.0.1", port=0, cert="", key=""):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass

        def send_json(self, code, payload):
            body = json.dumps(payload, allow_nan=False, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if code == 401: self.send_header("WWW-Authenticate", "Bearer")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/health": return self.send_json(200, {"ok": True})
            supplied = self.headers.get("Authorization", "").encode()
            if not hmac.compare_digest(supplied, ("Bearer " + token).encode()):
                return self.send_json(401, {"error": "unauthorized"})
            aliases = {"/api/v1/stats", "/stats" if store.source == "proxmox" else "/nas-stats"}
            if path not in aliases: return self.send_json(404, {"error": "not_found"})
            code, payload = store.payload()
            self.send_json(code, payload)

    server = StatsHTTPServer((host, port), Handler)
    if cert or key:
        if not cert or not key: raise ValueError("Both TLS cert and key are required")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True, do_handshake_on_connect=False)
    return server
