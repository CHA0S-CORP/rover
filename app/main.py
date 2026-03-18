import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import HLS_OUTPUT_DIR, CORS_ORIGINS
from app.novatek import NovatekClient
from app.stream import StreamManager

logging.basicConfig(level=logging.INFO)

novatek = NovatekClient()
stream_manager = StreamManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    HLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield
    await stream_manager.stop()
    await novatek.close()


app = FastAPI(title="Rover", lifespan=lifespan)

origins = [o.strip() for o in CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.api import router as api_router
from app.routes.files import router as files_router
from app.routes.stream import router as stream_router
from app.routes.embed import router as embed_router

app.include_router(api_router)
app.include_router(files_router)
app.include_router(stream_router)
app.include_router(embed_router)

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
