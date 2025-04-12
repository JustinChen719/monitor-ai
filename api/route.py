from fastapi import APIRouter
from fastapi.params import Path, Param, Depends, Body

from core import get_stream_controller, StreamController
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def index():
    return {"message": "Hello World"}


@router.get("/status")
async def status(stream_controller: StreamController = Depends(get_stream_controller)):
    pass
