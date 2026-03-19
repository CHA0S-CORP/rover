from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse

from app.config import HLS_OUTPUT_DIR

router = APIRouter()


def _manager():
    from app.main import stream_manager
    return stream_manager


# ── MJPEG (low latency, for <img> tag) ──

@router.get("/api/stream/mjpeg")
async def stream_mjpeg():
    """Proxy the camera's MJPEG stream. Use as: <img src="/api/stream/mjpeg">"""
    return StreamingResponse(
        _manager().proxy_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=arflebarfle",
        headers={"Cache-Control": "no-cache, no-store"},
    )


@router.get("/api/stream/snapshot")
async def stream_snapshot():
    """Single JPEG frame from the live stream."""
    frame = await _manager().get_snapshot()
    if frame is None:
        raise HTTPException(502, "No frame available")
    return Response(content=frame, media_type="image/jpeg",
                    headers={"Cache-Control": "no-cache, no-store"})


# ── HLS (embeddable <video>, ~5s latency) ──

@router.post("/api/stream/hls/start")
async def hls_start():
    await _manager().start_hls()
    return {"ok": True}


@router.post("/api/stream/hls/stop")
async def hls_stop():
    await _manager().stop_hls()
    return {"ok": True}


@router.get("/hls/{filename:path}")
async def serve_hls(filename: str):
    filepath = HLS_OUTPUT_DIR / filename
    if not filepath.is_file():
        raise HTTPException(404, "Segment not found")
    try:
        filepath.resolve().relative_to(HLS_OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")
    media_type = "application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/MP2T"
    return FileResponse(filepath, media_type=media_type,
                        headers={"Cache-Control": "no-cache, no-store"})


# ── Status ──

@router.get("/api/stream/status")
async def stream_status():
    return _manager().status()
