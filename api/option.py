from fastapi import APIRouter
from fastapi.params import Path, Param, Depends, Body

from api.response import create_ok_response, create_err_response
from core import get_stream_controller, StreamController
from utils import get_logger

logger = get_logger(__name__)
option = APIRouter(prefix="/option")


@option.post("/create_core")
async def create_core(
        username: str = Body(...),
        password: str = Body(...),
        ip: str = Body(...),
        port: int = Body(default=554),
        path: str = Body(default="/Streaming/Channels/102"),
        video_width: int = Body(default=640),
        video_height: int = Body(default=360),
        bytes_per_pixel: int = Body(default=3),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    core_id = stream_controller.create_core(
            username=username,
            password=password,
            ip=ip,
            port=port,
            path=path,
            video_width=video_width,
            video_height=video_height,
            bytes_per_pixel=bytes_per_pixel
    )
    return create_ok_response({"core_id": core_id})


@option.post("/start_core/{core_id}")
async def start_core(
        core_id: str = Path(...),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    if stream_controller.start_core(core_id):
        return create_ok_response(None)
    else:
        return create_err_response("启动失败")


@option.post("/stop_core/{core_id}")
async def stop_core(
        core_id: str = Path(...),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    if stream_controller.stop_core(core_id):
        return create_ok_response(None)
    return create_err_response("停止失败")


@option.delete("/delete_core/{core_id}")
async def delete_core(
        core_id: str = Path(...),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    if stream_controller.delete_core(core_id):
        return create_ok_response(None)
    return create_err_response("删除失败")

# @option.post("/enable_ai/{core_id}")
# async def enable_ai(
#         core_id: str = Path(...),
#         enable_ai: bool = Body(...),
#         stream_controller: StreamController = Depends(get_stream_controller)
# ):
#     if stream_controller.enable_ai(core_id, enable_ai):
#         return create_ok_response(None)
#     return create_err_response("启停AI失败")
