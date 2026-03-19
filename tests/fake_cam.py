"""Fake SigmaStar dashcam HTTP server for testing.

Mimics the actual camera's behavior:
- Command API returns XML with <Parameters> (not <Value>)
- File browsing via HTML directory listings (not cmd 3015)
- No RTSP stream
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading

# State that tests can inspect/mutate
state = {
    "recording": False,
    "recording_seconds": 0,
    "mode": 0,
    "photos_taken": 0,
    "deleted_files": [],
}

FAKE_VIDEO_LISTING = """\
<!DOCTYPE html><html><head><title>Index of /Video/</title></head><body>
<h1>Index of /Video/</h1><pre><table cellpadding="0">
<tr><th><a href="?nd">Name</a></th><th><a href="?dd">Modified</a></th><th><a href="?sd">Size</a></th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="..">Parent directory</a></td><td>&nbsp;-</td><td>&nbsp;&nbsp;-</td></tr>
<tr><td><a href="Front/">Front/</a></td><td>&nbsp;18-Mar-2026 19:10</td><td>&nbsp;&nbsp;[DIRECTORY]</td></tr>
<tr><td><a href="Rear/">Rear/</a></td><td>&nbsp;24-Aug-2025 22:31</td><td>&nbsp;&nbsp;[DIRECTORY]</td></tr>
</table></pre></body></html>
"""

FAKE_FRONT_LISTING = """\
<!DOCTYPE html><html><head><title>Index of /Video/Front/</title></head><body>
<h1>Index of /Video/Front/</h1><pre><table cellpadding="0">
<tr><th><a href="?nd">Name</a></th><th><a href="?dd">Modified</a></th><th><a href="?sd">Size</a></th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="..">Parent directory</a></td><td>&nbsp;-</td><td>&nbsp;&nbsp;-</td></tr>
<tr><td><a href="2026_0318_191000F.mp4">2026_0318_191000F.mp4</a></td><td>&nbsp;18-Mar-2026 19:10</td><td>&nbsp;&nbsp;52428800</td></tr>
<tr><td><a href="2026_0318_191500F.mp4">2026_0318_191500F.mp4</a></td><td>&nbsp;18-Mar-2026 19:15</td><td>&nbsp;&nbsp;104857600</td></tr>
</table></pre></body></html>
"""

FAKE_REAR_LISTING = """\
<!DOCTYPE html><html><head><title>Index of /Video/Rear/</title></head><body>
<h1>Index of /Video/Rear/</h1><pre><table cellpadding="0">
<tr><th><a href="?nd">Name</a></th><th><a href="?dd">Modified</a></th><th><a href="?sd">Size</a></th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="..">Parent directory</a></td><td>&nbsp;-</td><td>&nbsp;&nbsp;-</td></tr>
<tr><td><a href="2026_0318_191000R.mp4">2026_0318_191000R.mp4</a></td><td>&nbsp;18-Mar-2026 19:10</td><td>&nbsp;&nbsp;26214400</td></tr>
</table></pre></body></html>
"""

FAKE_PHOTO_LISTING = """\
<!DOCTYPE html><html><head><title>Index of /Photo/</title></head><body>
<h1>Index of /Photo/</h1><pre><table cellpadding="0">
<tr><th><a href="?nd">Name</a></th><th><a href="?dd">Modified</a></th><th><a href="?sd">Size</a></th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="..">Parent directory</a></td><td>&nbsp;-</td><td>&nbsp;&nbsp;-</td></tr>
<tr><td><a href="Front/">Front/</a></td><td>&nbsp;24-Aug-2025 22:31</td><td>&nbsp;&nbsp;[DIRECTORY]</td></tr>
</table></pre></body></html>
"""

FAKE_PHOTO_FRONT_LISTING = """\
<!DOCTYPE html><html><head><title>Index of /Photo/Front/</title></head><body>
<h1>Index of /Photo/Front/</h1><pre><table cellpadding="0">
<tr><th><a href="?nd">Name</a></th><th><a href="?dd">Modified</a></th><th><a href="?sd">Size</a></th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="..">Parent directory</a></td><td>&nbsp;-</td><td>&nbsp;&nbsp;-</td></tr>
</table></pre></body></html>
"""

FAKE_PROTECT_LISTING = """\
<!DOCTYPE html><html><head><title>Index of /Protect/</title></head><body>
<h1>Index of /Protect/</h1><pre><table cellpadding="0">
<tr><th><a href="?nd">Name</a></th><th><a href="?dd">Modified</a></th><th><a href="?sd">Size</a></th></tr>
<tr><td colspan="3"><hr></td></tr>
<tr><td><a href="..">Parent directory</a></td><td>&nbsp;-</td><td>&nbsp;&nbsp;-</td></tr>
</table></pre></body></html>
"""

DIR_LISTINGS = {
    "/Video/": FAKE_VIDEO_LISTING,
    "/Video/Front/": FAKE_FRONT_LISTING,
    "/Video/Rear/": FAKE_REAR_LISTING,
    "/Photo/": FAKE_PHOTO_LISTING,
    "/Photo/Front/": FAKE_PHOTO_FRONT_LISTING,
    "/Protect/": FAKE_PROTECT_LISTING,
}


def _xml_resp(cmd: int, status: int = 0, params: str | None = None, string: str | None = None) -> bytes:
    parts = [f'<?xml version="1.0" encoding="UTF-8" ?>\n<Function>\n<Cmd>{cmd}</Cmd>\n<Status>{status}</Status>']
    if params is not None:
        parts.append(f"<Parameters>{params}</Parameters>")
    if string is not None:
        parts.append(f"<String>{string}</String>")
    parts.append("</Function>")
    return "\n".join(parts).encode()


class FakeCamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        cmd = params.get("cmd", [None])[0]

        # Directory listings
        if cmd is None:
            path = parsed.path
            if not path.endswith("/"):
                path += "/"
            if path in DIR_LISTINGS:
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(DIR_LISTINGS[path].encode())
                return
            # File download
            if any(path.startswith(p) for p in ("/Video/", "/Photo/", "/Protect/")):
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.end_headers()
                self.wfile.write(b"\x00" * 1024)
                return
            self.send_response(404)
            self.end_headers()
            return

        cmd = int(cmd)
        par = params.get("par", [None])[0]
        str_param = params.get("str", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()

        match cmd:
            case 3016:  # Heartbeat
                self.wfile.write(_xml_resp(3016, status=-256))
            case 3019:  # Battery
                self.wfile.write(_xml_resp(3019))
            case 3017:  # Free space
                self.wfile.write(_xml_resp(3017, params="1"))
            case 3024:  # SD card
                self.wfile.write(_xml_resp(3024, params="2"))
            case 2016:  # Recording time
                secs = str(state["recording_seconds"]) if state["recording"] else "0"
                self.wfile.write(_xml_resp(2016, params=secs))
            case 2001:  # Start/stop recording
                if str_param == "1":
                    state["recording"] = True
                    state["recording_seconds"] = 1
                elif str_param == "0":
                    state["recording"] = False
                    state["recording_seconds"] = 0
                self.wfile.write(_xml_resp(2001))
            case 1001:  # Take photo
                state["photos_taken"] += 1
                self.wfile.write(_xml_resp(1001))
            case 3014:  # Config
                self.wfile.write(_xml_resp(3014, string="         "))
            case 3015:  # File list (returns count, not files)
                self.wfile.write(_xml_resp(3015, params="1"))
            case 4003:  # Delete file
                if str_param:
                    state["deleted_files"].append(str_param)
                self.wfile.write(_xml_resp(4003))
            case 3012:  # Firmware
                self.wfile.write(_xml_resp(3012, params="0"))
            case 3001:  # Set mode
                if par is not None:
                    state["mode"] = int(par)
                self.wfile.write(_xml_resp(3001))
            case _:
                self.wfile.write(_xml_resp(cmd, status=-256))

    def do_DELETE(self):
        parsed = urlparse(self.path)
        state["deleted_files"].append(parsed.path)
        self.send_response(200)
        self.end_headers()


class FakeCamServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.server = HTTPServer((host, port), FakeCamHandler)
        self.host = host
        self.port = self.server.server_address[1]
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self.server.shutdown()
        if self._thread:
            self._thread.join(timeout=5)

    def reset(self):
        state["recording"] = False
        state["recording_seconds"] = 0
        state["mode"] = 0
        state["photos_taken"] = 0
        state["deleted_files"] = []

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
