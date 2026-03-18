from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.novatek import NovatekClient

router = APIRouter(prefix="/api/files")


def _client() -> NovatekClient:
    from app.main import novatek
    return novatek


@router.get("")
async def list_files():
    try:
        files = await _client().get_file_list()
        return {"files": files}
    except Exception as e:
        raise HTTPException(502, str(e))


@router.get("/download")
async def download_file(path: str = Query(...)):
    client = _client()
    download_client = client.get_download_client()

    try:
        from app.config import CAM_FILE_BASE
        url = f"{CAM_FILE_BASE}{path}"
        req = download_client.build_request("GET", url)
        resp = await download_client.send(req, stream=True)
        resp.raise_for_status()
    except Exception as e:
        await download_client.aclose()
        raise HTTPException(502, f"Failed to fetch file: {e}")

    filename = path.split("\\")[-1].split("/")[-1]
    content_type = "video/mp4" if filename.lower().endswith(".mov") or filename.lower().endswith(".mp4") else "application/octet-stream"
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        content_type = "image/jpeg"

    async def stream():
        try:
            async for chunk in resp.aiter_bytes(chunk_size=65536):
                yield chunk
        finally:
            await resp.aclose()
            await download_client.aclose()

    return StreamingResponse(
        stream(),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/thumbnail")
async def thumbnail(path: str = Query(...)):
    client = _client()
    try:
        url = await client.get_thumbnail_url(path)
        async with client._client.stream("GET", url) as resp:
            resp.raise_for_status()
            data = await resp.aread()
        return StreamingResponse(iter([data]), media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(502, str(e))


@router.delete("")
async def delete_file(path: str = Query(...)):
    try:
        await _client().delete_file(path)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(502, str(e))
