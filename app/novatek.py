import xml.etree.ElementTree as ET

import httpx

from app.config import CAM_API_BASE, CAM_FILE_BASE, API_TIMEOUT


class NovatekError(Exception):
    pass


class NovatekClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=API_TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()

    async def _cmd(self, cmd: int, par: int | None = None) -> str:
        url = f"{CAM_API_BASE}&cmd={cmd}"
        if par is not None:
            url += f"&par={par}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.text

    async def _cmd_xml(self, cmd: int, par: int | None = None) -> ET.Element:
        text = await self._cmd(cmd, par)
        return ET.fromstring(text)

    async def ping(self) -> bool:
        try:
            await self._cmd(3016)
            return True
        except (httpx.HTTPError, OSError):
            return False

    async def get_status(self) -> dict:
        status: dict = {}
        try:
            root = await self._cmd_xml(3019)
            status["battery"] = root.findtext("Value", "unknown")
        except Exception:
            status["battery"] = "unknown"

        try:
            root = await self._cmd_xml(3017)
            status["free_space"] = root.findtext("Value", "unknown")
        except Exception:
            status["free_space"] = "unknown"

        try:
            root = await self._cmd_xml(3014)
            status["config"] = root.findtext("Value", "unknown")
        except Exception:
            status["config"] = "unknown"

        # Check recording state via cmd 2016
        try:
            root = await self._cmd_xml(2016)
            status["recording"] = root.findtext("Value", "0") == "1"
        except Exception:
            status["recording"] = False

        status["connected"] = True
        return status

    async def start_recording(self) -> str:
        return await self._cmd(2001, 1)

    async def stop_recording(self) -> str:
        return await self._cmd(2001, 0)

    async def take_photo(self) -> str:
        return await self._cmd(1001)

    async def get_config(self) -> ET.Element:
        return await self._cmd_xml(3014)

    async def set_mode(self, mode: int) -> str:
        """Set camera mode: 0=video, 1=photo, 2=preview."""
        return await self._cmd(3001, mode)

    async def get_file_list(self) -> list[dict]:
        root = await self._cmd_xml(3015)
        files = []
        for f in root.iter("File"):
            entry: dict = {}
            for child in f:
                entry[child.tag.lower()] = child.text
            if "fpath" in entry:
                entry["url"] = f"{CAM_FILE_BASE}{entry['fpath']}"
            files.append(entry)
        return files

    async def delete_file(self, path: str) -> str:
        return await self._cmd(4003, path)  # type: ignore[arg-type]

    async def get_thumbnail_url(self, path: str) -> str:
        return f"{CAM_API_BASE}&cmd=4001&str={path}"

    def get_download_client(self) -> httpx.AsyncClient:
        """Return a client with long timeout for file downloads."""
        return httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
