from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()

FAVICON_PATH = Path(__file__).resolve().parents[1] / 'public' / 'favicon.ico'
PNG_PATH = Path(__file__).resolve().parents[1] / 'public' / 'favicon.png'


@router.get('/favicon.ico', include_in_schema=False)
def favicon_ico():
    return FileResponse(FAVICON_PATH, media_type='image/x-icon')


@router.get('/favicon.png', include_in_schema=False)
def favicon_png():
    return FileResponse(PNG_PATH, media_type='image/png')
