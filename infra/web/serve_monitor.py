#!/usr/bin/env python3
"""Simple static server to serve the SomaBrain dashboard during development.

Run while Somabrain is running so you can open http://127.0.0.1:8083/dashboard.html
and view live metrics from http://127.0.0.1:9696/metrics. This server enables CORS
so the dashboard can fetch metrics from the Somabrain instance.

Usage:
    python infra/web/serve_monitor.py

Then open:
    http://127.0.0.1:8083/dashboard.html  (Unified Dashboard)
    http://127.0.0.1:8083/monitor.html    (Legacy Metrics Dashboard)
    http://127.0.0.1:8083/index.html      (Legacy Test UI)
"""

import os
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 8083


class CORSHandler(SimpleHTTPRequestHandler):
    """HTTP handler with CORS support and metrics proxy."""

    def do_GET(self):
        """Handle GET requests with metrics proxy support."""
        parsed = urllib.parse.urlparse(self.path)

        # Proxy /metrics requests to the target SomaBrain instance
        if parsed.path == "/metrics":
            qs = urllib.parse.parse_qs(parsed.query)
            target_port = qs.get("port", ["9696"])[0]
            target_url = f"http://127.0.0.1:{target_port}/metrics"
            try:
                with urllib.request.urlopen(target_url, timeout=5) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    self.wfile.write(data)
                return
            except Exception as e:
                self.send_error(502, f"Failed to fetch metrics: {e}")
                return

        # Redirect root to dashboard
        if self.path == "/" or self.path == "":
            self.send_response(302)
            self.send_header("Location", "/dashboard.html")
            self.end_headers()
            return

        # Default file serving
        super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()

    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()


def main():
    """Start the dashboard server."""
    webroot = os.path.dirname(os.path.abspath(__file__))
    os.chdir(webroot)

    print("=" * 60)
    print("SomaBrain Dashboard Server")
    print("=" * 60)
    print(f"Serving from: {webroot}")
    print("")
    print("Available pages:")
    print(f"  http://127.0.0.1:{PORT}/dashboard.html  (Unified Dashboard)")
    print(f"  http://127.0.0.1:{PORT}/monitor.html    (Metrics Dashboard)")
    print(f"  http://127.0.0.1:{PORT}/index.html      (Test UI)")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    with ThreadingHTTPServer(("0.0.0.0", PORT), CORSHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == "__main__":
    main()