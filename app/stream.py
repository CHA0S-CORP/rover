"""MJPEG proxy and HLS transcoder for SigmaStar dashcam.

The camera serves MJPEG on port 8192 (640x360@25fps, boundary "arflebarfle").
Two consumption modes:
  1. Direct MJPEG proxy — low latency, works in <img> tags
  2. ffmpeg MJPEG→HLS — embeddable <video> with hls.js, ~5s latency
"""

import asyncio
import logging
import shutil
import time

import httpx

from app.config import (
    CAM_STREAM_MJPEG, HLS_OUTPUT_DIR,
    HLS_SEGMENT_TIME, HLS_LIST_SIZE, STREAM_TIMEOUT,
)

log = logging.getLogger(__name__)


class StreamManager:
    def __init__(self) -> None:
        self._mjpeg_clients: int = 0
        self._last_frame: bytes | None = None
        self._last_frame_time: float = 0
        # HLS transcoder state
        self._hls_process: asyncio.subprocess.Process | None = None
        self._hls_running: bool = False
        self._hls_watch_task: asyncio.Task | None = None

    # ── Properties ──

    @property
    def mjpeg_active(self) -> bool:
        return self._mjpeg_clients > 0

    @property
    def hls_active(self) -> bool:
        return self._hls_running and self._hls_process is not None and self._hls_process.returncode is None

    # ── MJPEG proxy ──

    async def proxy_mjpeg(self):
        """Yield raw MJPEG multipart data from the camera."""
        self._mjpeg_clients += 1
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(STREAM_TIMEOUT, connect=5.0)) as client:
                async with client.stream("GET", CAM_STREAM_MJPEG) as resp:
                    resp.raise_for_status()
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        self._cache_frame(chunk)
                        yield chunk
        except (httpx.HTTPError, OSError) as e:
            log.warning("MJPEG stream ended: %s", e)
        finally:
            self._mjpeg_clients = max(0, self._mjpeg_clients - 1)

    def _cache_frame(self, chunk: bytes) -> None:
        start = chunk.find(b"\xff\xd8")
        if start == -1:
            return
        end = chunk.find(b"\xff\xd9", start)
        if end == -1:
            return
        self._last_frame = chunk[start:end + 2]
        self._last_frame_time = time.monotonic()

    async def get_snapshot(self) -> bytes | None:
        if self._last_frame and (time.monotonic() - self._last_frame_time) < 5.0:
            return self._last_frame
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
                async with client.stream("GET", CAM_STREAM_MJPEG) as resp:
                    buf = b""
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        buf += chunk
                        start = buf.find(b"\xff\xd8")
                        end = buf.find(b"\xff\xd9", start + 2) if start != -1 else -1
                        if start != -1 and end != -1:
                            self._last_frame = buf[start:end + 2]
                            self._last_frame_time = time.monotonic()
                            return self._last_frame
                        if len(buf) > 500_000:
                            break
        except Exception as e:
            log.warning("Snapshot failed: %s", e)
        return None

    # ── HLS transcoder (ffmpeg) ──

    def _clean_hls(self) -> None:
        if HLS_OUTPUT_DIR.exists():
            shutil.rmtree(HLS_OUTPUT_DIR)
        HLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async def start_hls(self) -> None:
        if self.hls_active:
            return
        self._clean_hls()
        self._hls_running = True
        cmd = [
            "ffmpeg", "-y",
            "-f", "mjpeg",
            "-i", CAM_STREAM_MJPEG,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-g", "50",
            "-f", "hls",
            "-hls_time", str(HLS_SEGMENT_TIME),
            "-hls_list_size", str(HLS_LIST_SIZE),
            "-hls_flags", "delete_segments+append_list",
            str(HLS_OUTPUT_DIR / "live.m3u8"),
        ]
        log.info("Starting HLS transcoder: %s", " ".join(cmd))
        self._hls_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        self._hls_watch_task = asyncio.create_task(self._watch_hls())

    async def _watch_hls(self) -> None:
        assert self._hls_process is not None
        stderr = b""
        try:
            data = await self._hls_process.stderr.read()  # type: ignore[union-attr]
            if data:
                stderr = data
        except Exception:
            pass
        await self._hls_process.wait()
        if not self._hls_running:
            return
        log.warning("ffmpeg exited with code %s", self._hls_process.returncode)
        if stderr:
            log.warning("ffmpeg stderr (last 500): %s", stderr[-500:].decode(errors="replace"))
        # Auto-restart with backoff
        for attempt in range(5):
            if not self._hls_running:
                return
            delay = min(2 ** attempt, 30)
            log.info("Restarting HLS in %ds (attempt %d)", delay, attempt + 1)
            await asyncio.sleep(delay)
            self._clean_hls()
            await self.start_hls()
            await asyncio.sleep(3)
            if self.hls_active:
                return
        log.error("HLS transcoder failed after all retries")
        self._hls_running = False

    async def stop_hls(self) -> None:
        self._hls_running = False
        if self._hls_process and self._hls_process.returncode is None:
            self._hls_process.terminate()
            try:
                await asyncio.wait_for(self._hls_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._hls_process.kill()
        if self._hls_watch_task and not self._hls_watch_task.done():
            self._hls_watch_task.cancel()
        self._hls_process = None

    # ── Status ──

    def status(self) -> dict:
        return {
            "mjpeg_clients": self._mjpeg_clients,
            "hls_active": self.hls_active,
            "hls_ready": (HLS_OUTPUT_DIR / "live.m3u8").exists(),
            "running": self.mjpeg_active or self.hls_active,
        }

    async def stop(self) -> None:
        await self.stop_hls()
