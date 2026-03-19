import os
from pathlib import Path

CAM_IP = os.environ.get("CAM_IP", "192.168.1.252")
CAM_API_BASE = f"http://{CAM_IP}/?custom=1"
CAM_STREAM_MJPEG = f"http://{CAM_IP}:8192"
CAM_STREAM_RTSP = f"rtsp://{CAM_IP}:554/"
CAM_FILE_BASE = f"http://{CAM_IP}"

HLS_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "hls"
HLS_SEGMENT_TIME = 2
HLS_LIST_SIZE = 5

API_TIMEOUT = 5.0
STREAM_TIMEOUT = 30.0

WEB_HOST = "0.0.0.0"
WEB_PORT = int(os.environ.get("WEB_PORT", "8080"))

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
