from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

EMBED_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Rover Stream</title>
<script src="https://cdn.jsdelivr.net/npm/hls.js@1"></script>
<style>
*{margin:0;padding:0}
html,body{width:100%;height:100%;overflow:hidden;background:#000}
video{width:100%;height:100%;object-fit:contain}
#msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#888;font-family:sans-serif;font-size:1.2rem}
</style>
</head>
<body>
<div id="msg">Connecting...</div>
<video id="v" muted autoplay playsinline></video>
<script>
const video = document.getElementById("v");
const msg = document.getElementById("msg");

// Resolve HLS URL relative to this page's origin (works when embedded cross-origin)
const base = new URL(".", document.currentScript ? document.currentScript.src : location.href).origin;
const hlsUrl = base + "/hls/live.m3u8";

let hls;
let started = false;

async function ensureStream() {
    try {
        const res = await fetch(base + "/api/stream/status");
        const s = await res.json();
        if (!s.running) {
            msg.textContent = "Starting stream...";
            await fetch(base + "/api/stream/start", { method: "POST" });
            await new Promise(r => setTimeout(r, 3000));
        }
        started = true;
        initPlayer();
    } catch(e) {
        msg.textContent = "Cannot reach Rover";
        setTimeout(ensureStream, 5000);
    }
}

function initPlayer() {
    msg.style.display = "none";
    if (Hls.isSupported()) {
        hls = new Hls({ liveSyncDurationCount: 3, liveMaxLatencyDurationCount: 5 });
        hls.loadSource(hlsUrl);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
        hls.on(Hls.Events.ERROR, (_e, data) => {
            if (data.fatal) {
                msg.style.display = "flex";
                msg.textContent = "Stream interrupted, retrying...";
                hls.destroy();
                setTimeout(initPlayer, 3000);
            }
        });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = hlsUrl;
        video.addEventListener("loadedmetadata", () => video.play());
    } else {
        msg.style.display = "flex";
        msg.textContent = "HLS not supported in this browser";
    }
}

ensureStream();
</script>
</body>
</html>
"""


@router.get("/embed", response_class=HTMLResponse)
async def embed_player():
    """Minimal self-contained HLS player page for iframe embedding."""
    return EMBED_HTML


@router.get("/embed/snippet")
async def embed_snippet():
    """Returns HTML snippet for embedding the stream in an external page."""
    return {
        "iframe": '<iframe src="{rover_url}/embed" style="width:640px;height:360px;border:none" allow="autoplay" allowfullscreen></iframe>',
        "hls_url": "/hls/live.m3u8",
        "note": "Replace {rover_url} with your Rover instance URL, e.g. http://raspberrypi:8080",
    }
