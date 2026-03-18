import asyncio
import logging
import shutil

from app.config import CAM_STREAM_RTSP, CAM_STREAM_HTTP, HLS_OUTPUT_DIR, HLS_SEGMENT_TIME, HLS_LIST_SIZE

log = logging.getLogger(__name__)


class StreamManager:
    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._running = False
        self._restart_task: asyncio.Task | None = None
        self._use_http_fallback = False

    @property
    def running(self) -> bool:
        return self._running and self._process is not None and self._process.returncode is None

    def _clean_hls(self) -> None:
        if HLS_OUTPUT_DIR.exists():
            shutil.rmtree(HLS_OUTPUT_DIR)
        HLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _build_cmd(self) -> list[str]:
        source = CAM_STREAM_HTTP if self._use_http_fallback else CAM_STREAM_RTSP
        cmd = ["ffmpeg", "-y"]
        if not self._use_http_fallback:
            cmd += ["-fflags", "nobuffer", "-rtsp_transport", "tcp"]
        cmd += [
            "-i", source,
            "-c:v", "copy",
            "-c:a", "aac",
            "-f", "hls",
            "-hls_time", str(HLS_SEGMENT_TIME),
            "-hls_list_size", str(HLS_LIST_SIZE),
            "-hls_flags", "delete_segments+append_list",
            str(HLS_OUTPUT_DIR / "live.m3u8"),
        ]
        return cmd

    async def start(self) -> None:
        if self.running:
            return
        self._clean_hls()
        self._use_http_fallback = False
        self._running = True
        await self._launch()

    async def _launch(self) -> None:
        cmd = self._build_cmd()
        log.info("Starting stream: %s", " ".join(cmd))
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        self._restart_task = asyncio.create_task(self._watch())

    async def _watch(self) -> None:
        assert self._process is not None
        stderr = b""
        try:
            stderr_data = await self._process.stderr.read()  # type: ignore[union-attr]
            if stderr_data:
                stderr = stderr_data
        except Exception:
            pass
        await self._process.wait()

        if not self._running:
            return

        log.warning("ffmpeg exited with code %s", self._process.returncode)
        if stderr:
            log.warning("ffmpeg stderr (last 500 chars): %s", stderr[-500:].decode(errors="replace"))

        # Try HTTP fallback if RTSP failed
        if not self._use_http_fallback:
            log.info("Retrying with HTTP stream fallback")
            self._use_http_fallback = True
            self._clean_hls()
            await self._launch()
            return

        # Exponential backoff restart
        for attempt in range(5):
            if not self._running:
                return
            delay = min(2 ** attempt, 30)
            log.info("Restarting stream in %ds (attempt %d)", delay, attempt + 1)
            await asyncio.sleep(delay)
            self._clean_hls()
            self._use_http_fallback = False
            await self._launch()
            # Wait a moment to see if it stays up
            await asyncio.sleep(3)
            if self.running:
                return

        log.error("Stream failed after all retries")
        self._running = False

    async def stop(self) -> None:
        self._running = False
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
        if self._restart_task and not self._restart_task.done():
            self._restart_task.cancel()
        self._process = None

    def status(self) -> dict:
        return {
            "running": self.running,
            "fallback": self._use_http_fallback,
            "hls_ready": (HLS_OUTPUT_DIR / "live.m3u8").exists(),
        }
