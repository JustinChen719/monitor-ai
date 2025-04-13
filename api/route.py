from fastapi import APIRouter
from fastapi.params import Path, Param, Depends, Body

from api.response import *
from core import get_stream_controller, StreamController
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def index():
    return create_ok_response({"message": "Hello World"})


@router.get("/status/{core_id}")
async def status(
        core_id: str = Path(..., description="Core ID"),
        stream_controller: StreamController = Depends(get_stream_controller)
):
    core_status = stream_controller.get_core_status(core_id)
    if core_status is None:
        return create_err_response("Core not found")
    return create_ok_response(core_status)


@router.get("/status")
async def all_status(
        stream_controller: StreamController = Depends(get_stream_controller)
):
    cores_status = stream_controller.get_all_cores_status()
    return create_ok_response(cores_status)
