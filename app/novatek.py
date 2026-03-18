import xml.etree.ElementTree as ET

import httpx

from app.config import CAM_API_BASE, CAM_FILE_BASE, API_TIMEOUT

BATTERY_LEVELS = {
    "0": "Full",
    "1": "Medium",
    "2": "Low",
    "3": "Empty",
    "4": "Unknown",
    "5": "Charging",
}

SD_STATUS = {
    "0": "Removed",
    "1": "Inserted",
    "2": "Locked",
}


class NovatekError(Exception):
    pass


class NovatekClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=API_TIMEOUT)

    async def close(self) -> None:
        await self._client.aclose()

    async def _cmd(self, cmd: int, par: int | None = None, str_param: str | None = None) -> str:
        url = f"{CAM_API_BASE}&cmd={cmd}"
        if par is not None:
            url += f"&par={par}"
        if str_param is not None:
            url += f"&str={str_param}"
        resp = await self._client.get(url)
        resp.raise_for_status()
        return resp.text

    async def _cmd_xml(self, cmd: int, par: int | None = None, str_param: str | None = None) -> ET.Element:
        text = await self._cmd(cmd, par, str_param)
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
            raw = root.findtext("Value", "unknown")
            status["battery"] = BATTERY_LEVELS.get(raw, raw)
        except Exception:
            status["battery"] = "unknown"

        try:
            root = await self._cmd_xml(3017)
            status["free_space"] = root.findtext("Value", "unknown")
        except Exception:
            status["free_space"] = "unknown"

        try:
            root = await self._cmd_xml(3024)
            raw = root.findtext("Value", "unknown")
            status["sd_card"] = SD_STATUS.get(raw, raw)
        except Exception:
            status["sd_card"] = "unknown"

        # Recording time > 0 means recording is active
        try:
            root = await self._cmd_xml(2016)
            rec_time = root.findtext("Value", "0")
            status["recording"] = int(rec_time) > 0
            status["recording_seconds"] = int(rec_time)
        except Exception:
            status["recording"] = False
            status["recording_seconds"] = 0

        status["connected"] = True
        return status

    async def start_recording(self) -> str:
        return await self._cmd(2001, str_param="1")

    async def stop_recording(self) -> str:
        return await self._cmd(2001, str_param="0")

    async def take_photo(self) -> str:
        return await self._cmd(1001)

    async def get_config(self) -> ET.Element:
        return await self._cmd_xml(3014)

    async def set_mode(self, mode: int) -> str:
        """Set camera mode: 0=video, 1=photo, 2=playback."""
        return await self._cmd(3001, par=mode)

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
        return await self._cmd(4003, str_param=path)

    async def get_thumbnail_url(self, path: str) -> str:
        return f"{CAM_API_BASE}&cmd=4001&str={path}"

    async def get_firmware_version(self) -> str:
        root = await self._cmd_xml(3012)
        return root.findtext("String", "unknown")

    def get_download_client(self) -> httpx.AsyncClient:
        """Return a client with long timeout for file downloads."""
        return httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
