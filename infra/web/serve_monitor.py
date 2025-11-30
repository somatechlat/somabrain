import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from common.logging import logger

"""Simple static server to serve the monitoring dashboard during development.

Run while Somabrain is running so you can open http://127.0.0.1:8081/monitor.html
and view live metrics from http://127.0.0.1:9696/metrics. This server enables CORS
so the dashboard can fetch metrics from the Somabrain instance.
"""


PORT = 8083  # Use a distinct port and bind to all interfaces so the dashboard is reachable.
HANDLER_CLASS = SimpleHTTPRequestHandler


class CORSHandler(HANDLER_CLASS):
    pass
def do_GET(self):
        # Parse URL and query parameters
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/metrics":
            # Expected query: ?port=9696 (local/docker or k8s cluster)
            qs = urllib.parse.parse_qs(parsed.query)
            target_port = qs.get("port", ["9696"])[0]
            target_url = f"http://127.0.0.1:{target_port}/metrics"
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                with urllib.request.urlopen(target_url) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4")
                    self.end_headers()
                    self.wfile.write(data)
                return
            except Exception as e:
                logger.exception("Exception caught: %s", e)
                raise
        # Use default handling for other paths
        super().do_GET()

def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()


if __name__ == "__main__":
    pass

    webroot = os.path.join(os.path.dirname(__file__), ".")
    os.chdir(webroot)
    # Bind to 0.0.0.0 to accept connections from any host (including localhost).
    with ThreadingHTTPServer(("0.0.0.0", PORT), CORSHandler) as httpd:
        print(f"Serving dashboard at http://127.0.0.1:{PORT}/monitor.html")
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("shutting down")
