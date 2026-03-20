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
<script src="https://cdn.jsdelivr.net/npm/hls.js@1/dist/hls.min.js"></script>
<style>
*{margin:0;padding:0}
html,body{width:100%;height:100%;overflow:hidden;background:#000}
video,img{width:100%;height:100%;object-fit:contain}
#msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#888;font-family:sans-serif;font-size:1.2rem}
</style>
</head>
<body>
<div id="msg">Connecting...</div>
<video id="v" muted autoplay playsinline style="display:none"></video>
<img id="mjpeg" style="display:none" alt="">
<script>
const video = document.getElementById("v");
const mjpeg = document.getElementById("mjpeg");
const msg = document.getElementById("msg");
const base = location.origin;

// Try RTSP HLS first (1080p, no transcode), fall back to MJPEG
async function init() {
    try {
        const status = await fetch(base + "/api/stream/status").then(r => r.json());
        if (!status.rtsp_hls_active && !status.hls_active) {
            msg.textContent = "Starting 1080p stream...";
            await fetch(base + "/api/stream/rtsp/start", { method: "POST" });
        }
        for (let i = 0; i < 15; i++) {
            await new Promise(r => setTimeout(r, 1000));
            const check = await fetch(base + "/api/stream/status").then(r => r.json());
            if (check.hls_ready) { startHls(); return; }
        }
    } catch(e) {}
    // Fall back to MJPEG
    startMjpeg();
}

function startHls() {
    msg.style.display = "none";
    video.style.display = "block";
    const src = base + "/hls/live.m3u8";
    if (Hls.isSupported()) {
        const hls = new Hls({ liveSyncDurationCount: 3, liveMaxLatencyDurationCount: 5 });
        hls.loadSource(src);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => video.play());
        hls.on(Hls.Events.ERROR, (_e, data) => {
            if (data.fatal) {
                hls.destroy();
                startMjpeg();
            }
        });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = src;
        video.play();
    } else {
        startMjpeg();
    }
}

function startMjpeg() {
    msg.style.display = "none";
    video.style.display = "none";
    mjpeg.style.display = "block";
    mjpeg.src = base + "/api/stream/mjpeg?" + Date.now();
    mjpeg.onerror = () => {
        msg.style.display = "flex";
        msg.textContent = "Stream unavailable";
        setTimeout(init, 5000);
    };
}

init();
</script>
</body>
</html>
"""


@router.get("/embed", response_class=HTMLResponse)
async def embed_player():
    """Embeddable stream player. Uses HLS if available, falls back to MJPEG."""
    return EMBED_HTML


@router.get("/embed/snippet")
async def embed_snippet():
    return {
        "iframe": '<iframe src="{rover_url}/embed" style="width:640px;height:360px;border:none" allow="autoplay" allowfullscreen></iframe>',
        "mjpeg": '<img src="{rover_url}/api/stream/mjpeg" style="width:640px;height:360px">',
        "hls_url": "/hls/live.m3u8",
        "snapshot_url": "/api/stream/snapshot",
        "note": "Replace {rover_url} with your Rover URL. Start HLS first: POST /api/stream/hls/start",
    }
