"""Tests for the dashcam client against the fake camera server."""

import pytest

from tests.fake_cam import FakeCamServer, state
from app.novatek import NovatekClient


@pytest.fixture(scope="module")
def fake_cam():
    server = FakeCamServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def cam_client(fake_cam, monkeypatch):
    monkeypatch.setattr("app.config.CAM_API_BASE", f"{fake_cam.base_url}/?custom=1")
    monkeypatch.setattr("app.config.CAM_FILE_BASE", fake_cam.base_url)
    monkeypatch.setattr("app.novatek.CAM_API_BASE", f"{fake_cam.base_url}/?custom=1")
    monkeypatch.setattr("app.novatek.CAM_FILE_BASE", fake_cam.base_url)
    fake_cam.reset()
    return NovatekClient()


@pytest.mark.asyncio
async def test_ping(cam_client):
    assert await cam_client.ping() is True


@pytest.mark.asyncio
async def test_status_connected(cam_client):
    s = await cam_client.get_status()
    assert s["connected"] is True


@pytest.mark.asyncio
async def test_status_battery(cam_client):
    s = await cam_client.get_status()
    # Camera returns Status=0 with no value — client should return "OK"
    assert s["battery"] == "OK"


@pytest.mark.asyncio
async def test_status_free_space(cam_client):
    s = await cam_client.get_status()
    assert s["free_space"] == "1"


@pytest.mark.asyncio
async def test_status_sd_card(cam_client):
    s = await cam_client.get_status()
    assert s["sd_card"] == "Present"


@pytest.mark.asyncio
async def test_status_not_recording(cam_client):
    s = await cam_client.get_status()
    assert s["recording"] is False
    assert s["recording_seconds"] == 0


@pytest.mark.asyncio
async def test_start_recording(cam_client):
    await cam_client.start_recording()
    assert state["recording"] is True


@pytest.mark.asyncio
async def test_stop_recording(cam_client):
    await cam_client.start_recording()
    await cam_client.stop_recording()
    assert state["recording"] is False


@pytest.mark.asyncio
async def test_recording_shows_in_status(cam_client):
    await cam_client.start_recording()
    s = await cam_client.get_status()
    assert s["recording"] is True
    assert s["recording_seconds"] > 0


@pytest.mark.asyncio
async def test_take_photo(cam_client):
    await cam_client.take_photo()
    assert state["photos_taken"] == 1


@pytest.mark.asyncio
async def test_file_list_via_http_browsing(cam_client):
    files = await cam_client.get_file_list()
    # Should find 2 front videos + 1 rear video = 3 files
    assert len(files) == 3
    names = [f["name"] for f in files]
    assert "2026_0318_191000F.mp4" in names
    assert "2026_0318_191500F.mp4" in names
    assert "2026_0318_191000R.mp4" in names


@pytest.mark.asyncio
async def test_file_list_has_paths_and_urls(cam_client):
    files = await cam_client.get_file_list()
    for f in files:
        assert "fpath" in f
        assert "url" in f
        assert f["url"].startswith("http://")
        assert f["fpath"].startswith("/")


@pytest.mark.asyncio
async def test_file_list_has_category_and_camera(cam_client):
    files = await cam_client.get_file_list()
    front_files = [f for f in files if f.get("camera") == "front"]
    rear_files = [f for f in files if f.get("camera") == "rear"]
    assert len(front_files) == 2
    assert len(rear_files) == 1
    for f in files:
        assert f["category"] == "video"


@pytest.mark.asyncio
async def test_delete_file(cam_client):
    path = "/Video/Front/2026_0318_191000F.mp4"
    await cam_client.delete_file(path)
    assert path in state["deleted_files"]


@pytest.mark.asyncio
async def test_set_mode(cam_client):
    await cam_client.set_mode(1)
    assert state["mode"] == 1
    await cam_client.set_mode(0)
    assert state["mode"] == 0


@pytest.mark.asyncio
async def test_get_firmware_version(cam_client):
    version = await cam_client.get_firmware_version()
    # Camera returns Parameters=0, client should return "unknown"
    assert version == "unknown"


@pytest.mark.asyncio
async def test_get_config(cam_client):
    cfg = await cam_client.get_config()
    assert cfg["status"] == "0"
