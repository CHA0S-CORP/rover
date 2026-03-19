"""Tests for the FastAPI routes against the fake camera server."""

import pytest
from httpx import ASGITransport, AsyncClient

from tests.fake_cam import FakeCamServer, state


@pytest.fixture(scope="module")
def fake_cam():
    server = FakeCamServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def patch_cam(fake_cam, monkeypatch):
    monkeypatch.setattr("app.config.CAM_API_BASE", f"{fake_cam.base_url}/?custom=1")
    monkeypatch.setattr("app.config.CAM_FILE_BASE", fake_cam.base_url)
    monkeypatch.setattr("app.novatek.CAM_API_BASE", f"{fake_cam.base_url}/?custom=1")
    monkeypatch.setattr("app.novatek.CAM_FILE_BASE", fake_cam.base_url)
    fake_cam.reset()


@pytest.fixture
async def client(patch_cam):
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_status_endpoint(client):
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["sd_card"] == "Present"


@pytest.mark.asyncio
async def test_record_start_stop(client):
    resp = await client.post("/api/record/start")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert state["recording"] is True

    resp = await client.post("/api/record/stop")
    assert resp.status_code == 200
    assert state["recording"] is False


@pytest.mark.asyncio
async def test_take_photo_endpoint(client):
    resp = await client.post("/api/photo")
    assert resp.status_code == 200
    assert state["photos_taken"] == 1


@pytest.mark.asyncio
async def test_set_mode_endpoint(client):
    resp = await client.post("/api/mode", json={"mode": 1})
    assert resp.status_code == 200
    assert state["mode"] == 1


@pytest.mark.asyncio
async def test_set_mode_invalid(client):
    resp = await client.post("/api/mode", json={"mode": 5})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_config_endpoint(client):
    resp = await client.get("/api/config")
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_files_list(client):
    resp = await client.get("/api/files")
    assert resp.status_code == 200
    files = resp.json()["files"]
    assert len(files) == 3


@pytest.mark.asyncio
async def test_files_delete(client):
    path = "/Video/Front/2026_0318_191000F.mp4"
    resp = await client.request("DELETE", f"/api/files?path={path}")
    assert resp.status_code == 200
    assert path in state["deleted_files"]


@pytest.mark.asyncio
async def test_stream_status(client):
    resp = await client.get("/api/stream/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["running"] is False
    assert "hls_active" in data
    assert "mjpeg_clients" in data


@pytest.mark.asyncio
async def test_embed_page(client):
    resp = await client.get("/embed")
    assert resp.status_code == 200
    assert "hls.js" in resp.text
    assert "mjpeg" in resp.text


@pytest.mark.asyncio
async def test_embed_snippet(client):
    resp = await client.get("/embed/snippet")
    assert resp.status_code == 200
    data = resp.json()
    assert "iframe" in data
    assert "mjpeg" in data
    assert "hls_url" in data
