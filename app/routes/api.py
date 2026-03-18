from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.novatek import NovatekClient, NovatekError

router = APIRouter(prefix="/api")


def _client() -> NovatekClient:
    from app.main import novatek
    return novatek


@router.get("/status")
async def status():
    client = _client()
    try:
        return await client.get_status()
    except Exception:
        return {"connected": False, "error": "Camera not reachable"}


@router.post("/record/start")
async def record_start():
    try:
        await _client().start_recording()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.post("/record/stop")
async def record_stop():
    try:
        await _client().stop_recording()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.post("/photo")
async def take_photo():
    try:
        await _client().take_photo()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/config")
async def config():
    try:
        import xml.etree.ElementTree as ET
        root = await _client().get_config()
        return {"config": ET.tostring(root, encoding="unicode")}
    except Exception as e:
        raise HTTPException(502, str(e))


class ModeRequest(BaseModel):
    mode: int


@router.post("/mode")
async def set_mode(req: ModeRequest):
    if req.mode not in (0, 1, 2):
        raise HTTPException(400, "Mode must be 0 (video), 1 (photo), or 2 (playback)")
    try:
        await _client().set_mode(req.mode)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(502, str(e))
