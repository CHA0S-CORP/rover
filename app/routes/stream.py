from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import HLS_OUTPUT_DIR

router = APIRouter()


def _manager():
    from app.main import stream_manager
    return stream_manager


@router.post("/api/stream/start")
async def stream_start():
    await _manager().start()
    return {"ok": True}


@router.post("/api/stream/stop")
async def stream_stop():
    await _manager().stop()
    return {"ok": True}


@router.get("/api/stream/status")
async def stream_status():
    return _manager().status()


@router.get("/hls/{filename:path}")
async def serve_hls(filename: str):
    filepath = HLS_OUTPUT_DIR / filename
    if not filepath.is_file():
        raise HTTPException(404, "Segment not found")

    # Ensure path doesn't escape HLS directory
    try:
        filepath.resolve().relative_to(HLS_OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Forbidden")

    media_type = "application/vnd.apple.mpegurl" if filename.endswith(".m3u8") else "video/MP2T"
    return FileResponse(
        filepath,
        media_type=media_type,
        headers={"Cache-Control": "no-cache, no-store"},
    )
