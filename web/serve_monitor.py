"""Simple static server to serve the monitoring dashboard during development.

Run while Somabrain is running so you can open http://127.0.0.1:8081/monitor.html
and view live metrics from http://127.0.0.1:9696/metrics. This server enables CORS
so the dashboard can fetch metrics from the Somabrain instance.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 8081
HANDLER_CLASS = SimpleHTTPRequestHandler


class CORSHandler(HANDLER_CLASS):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()


if __name__ == "__main__":
    import os

    webroot = os.path.join(os.path.dirname(__file__), ".")
    os.chdir(webroot)
    with ThreadingHTTPServer(("127.0.0.1", PORT), CORSHandler) as httpd:
        print(f"Serving dashboard at http://127.0.0.1:{PORT}/monitor.html")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("shutting down")
