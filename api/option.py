from fastapi import APIRouter
from fastapi.params import Path, Param, Depends, Body

from core import get_stream_controller, StreamController
from utils import get_logger

logger = get_logger(__name__)
option = APIRouter(prefix="/option")


@option.post("/create_core")
async def create_core(
        key: str = Body(...),
        video_width: int = Body(default=1280),
        video_height: int = Body(default=720),
        bytes_per_pixel: int = Body(default=3),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    core_id = stream_controller.create_core(
            key=key,
            video_width=video_width,
            video_height=video_height,
            bytes_per_pixel=bytes_per_pixel
    )
    return {
        "data": {"core_id": core_id},
        "error": False,
        "message": ""
    }


@option.delete("/delete_core/{core_id}")
async def delete_core(
        core_id: str = Path(...),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    stream_controller.delete_core(core_id)
    return {
        "error": False,
        "message": ""
    }
