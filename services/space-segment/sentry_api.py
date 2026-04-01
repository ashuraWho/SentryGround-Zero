import http.server
import os
import socketserver
import subprocess
import sys
from urllib.parse import parse_qs, unquote, urlparse

PORT = 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/scan":
            self.send_response(404)
            self.end_headers()
            return

        qs = parse_qs(parsed.query)
        mode_raw = qs.get("mode", ["default"])[0]
        observation_mode = unquote(mode_raw).strip() or "default"
        mission_profile = os.getenv("MISSION_PROFILE", "dark_matter")

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header("X-Mission-Profile", mission_profile)
        self.send_header("X-Observation-Mode", observation_mode)
        self.end_headers()

        bin_path = os.getenv("SENTRY_BIN", "./core_engine/build/sentry_sat_sim")

        try:
            env = os.environ.copy()
            env["OBSERVATION_MODE"] = observation_mode
            meta_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "ai_training", "obc_model_meta.json"
            )
            env["SENTRY_OBC_META"] = meta_path

            proc = subprocess.run([bin_path], capture_output=True, env=env)
            self.wfile.write(proc.stdout)
            print(
                f"[API] profile={mission_profile} mode={observation_mode} "
                f"bytes={len(proc.stdout)}",
                file=sys.stderr,
            )
        except Exception as e:
            error_msg = f"Failed to execute SentrySat: {e}".encode()
            self.wfile.write(error_msg)
            print(error_msg.decode(), file=sys.stderr)


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"SentrySat Orbital API listening on port {PORT}", file=sys.stderr)
        httpd.serve_forever()
