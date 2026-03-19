"""Client for SigmaStar-based dashcam HTTP API.

This camera exposes:
- A Novatek-like command API at /?custom=1&cmd=... but with different
  response semantics (uses <Parameters> instead of <Value>, many commands
  return minimal info).
- An HTTP file server with HTML directory listings at / (directories:
  /Video/Front/, /Video/Rear/, /Photo/Front/, /Photo/Rear/, /Protect/).
"""

import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import httpx

from app.config import CAM_API_BASE, CAM_FILE_BASE, API_TIMEOUT

SD_STATUS = {
    "0": "No SD",
    "1": "Ready",
    "2": "Present",
}


class NovatekError(Exception):
    pass


class _DirListingParser(HTMLParser):
    """Parse the camera's HTML directory listing into file entries."""

    def __init__(self):
        super().__init__()
        self.entries: list[dict] = []
        self._in_td = False
        self._row: list[str] = []
        self._href: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
            self._href = None
        elif tag == "td":
            self._in_td = True
        elif tag == "a" and self._in_td:
            for name, val in attrs:
                if name == "href" and val not in ("..", "?nd", "?dd", "?sd"):
                    self._href = val

    def handle_endtag(self, tag):
        if tag == "td":
            self._in_td = False
        elif tag == "tr":
            if self._href and len(self._row) >= 1:
                name = self._href.rstrip("/")
                is_dir = self._href.endswith("/")
                # Extract date and size from row text
                date_str = self._row[1].strip().replace("\xa0", " ") if len(self._row) > 1 else ""
                size_str = self._row[2].strip().replace("\xa0", " ") if len(self._row) > 2 else ""
                if not is_dir and name and name != "Parent directory" and not name.startswith("."):
                    self.entries.append({
                        "name": name,
                        "date": date_str.strip(" -"),
                        "size": size_str.strip(" -"),
                    })
                elif is_dir and name and name != "Parent directory" and not name.startswith(".") and not name.startswith("System"):
                    self.entries.append({
                        "name": name,
                        "is_dir": True,
                        "date": date_str.strip(" -"),
                    })
            self._row = []
            self._href = None

    def handle_data(self, data):
        if self._in_td:
            self._row.append(data)


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

    def _xml_param(self, root: ET.Element) -> str | None:
        """Extract value from response — tries Parameters, Value, String."""
        for tag in ("Parameters", "Value", "String"):
            val = root.findtext(tag)
            if val is not None and val.strip():
                return val.strip()
        return None

    async def ping(self) -> bool:
        try:
            await self._cmd(3016)
            return True
        except (httpx.HTTPError, OSError):
            return False

    async def get_status(self) -> dict:
        status: dict = {}

        # Battery — cmd 3019 returns Status only on this camera
        try:
            root = await self._cmd_xml(3019)
            val = self._xml_param(root)
            st = root.findtext("Status", "-1")
            status["battery"] = val if val else ("OK" if st == "0" else "unknown")
        except Exception:
            status["battery"] = "unknown"

        # Free space — cmd 3017
        try:
            root = await self._cmd_xml(3017)
            val = self._xml_param(root)
            status["free_space"] = val if val else "unknown"
        except Exception:
            status["free_space"] = "unknown"

        # SD card — cmd 3024
        try:
            root = await self._cmd_xml(3024)
            val = self._xml_param(root)
            status["sd_card"] = SD_STATUS.get(val, val) if val else "unknown"
        except Exception:
            status["sd_card"] = "unknown"

        # Recording time — cmd 2016
        try:
            root = await self._cmd_xml(2016)
            val = self._xml_param(root)
            rec_time = int(val) if val and val.isdigit() else 0
            status["recording"] = rec_time > 0
            status["recording_seconds"] = rec_time
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

    async def get_config(self) -> dict:
        """Return raw config XML as a dict."""
        try:
            root = await self._cmd_xml(3014)
            return {
                "cmd": root.findtext("Cmd"),
                "status": root.findtext("Status"),
                "string": (root.findtext("String") or "").strip(),
                "parameters": root.findtext("Parameters"),
            }
        except Exception:
            return {}

    async def set_mode(self, mode: int) -> str:
        """Set camera mode: 0=video, 1=photo, 2=playback."""
        return await self._cmd(3001, par=mode)

    async def _browse_dir(self, path: str) -> list[dict]:
        """Fetch and parse an HTTP directory listing from the camera."""
        url = f"{CAM_FILE_BASE}/{path.strip('/')}/"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPError, OSError):
            return []
        parser = _DirListingParser()
        parser.feed(resp.text)
        return parser.entries

    async def get_file_list(self) -> list[dict]:
        """Recursively browse the camera's SD card via HTTP directory listings."""
        files: list[dict] = []
        # Known directories on this camera
        for top_dir in ("Video", "Photo", "Protect"):
            entries = await self._browse_dir(top_dir)
            for entry in entries:
                if entry.get("is_dir"):
                    # Descend one level (e.g., Video/Front/, Video/Rear/)
                    sub_path = f"{top_dir}/{entry['name']}"
                    sub_entries = await self._browse_dir(sub_path)
                    for sub in sub_entries:
                        if not sub.get("is_dir"):
                            sub["fpath"] = f"/{sub_path}/{sub['name']}"
                            sub["url"] = f"{CAM_FILE_BASE}/{sub_path}/{sub['name']}"
                            sub["category"] = top_dir.lower()
                            sub["camera"] = entry["name"].lower()
                            files.append(sub)
                elif not entry.get("is_dir"):
                    entry["fpath"] = f"/{top_dir}/{entry['name']}"
                    entry["url"] = f"{CAM_FILE_BASE}/{top_dir}/{entry['name']}"
                    entry["category"] = top_dir.lower()
                    files.append(entry)
        return files

    async def delete_file(self, path: str) -> str:
        """Delete via cmd 4003. Falls back to HTTP DELETE."""
        try:
            return await self._cmd(4003, str_param=path)
        except Exception:
            resp = await self._client.request("DELETE", f"{CAM_FILE_BASE}{path}")
            resp.raise_for_status()
            return resp.text

    async def get_firmware_version(self) -> str:
        try:
            root = await self._cmd_xml(3012)
            val = self._xml_param(root)
            return val if val and val != "0" else "unknown"
        except Exception:
            return "unknown"

    def get_download_client(self) -> httpx.AsyncClient:
        """Return a client with long timeout for file downloads."""
        return httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
