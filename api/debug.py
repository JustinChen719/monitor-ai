import cv2
import numpy as np

from starlette.responses import StreamingResponse, Response
from fastapi import APIRouter
from fastapi.params import Path, Param

from core import get_stream_controller
from utils import get_logger

logger = get_logger(__name__)

debug = APIRouter(prefix="/debug")


def generate_frames(core_id: str | None):
    stream_controller = get_stream_controller()
    queues = stream_controller.display_queues.get_all_queues()
    if core_id is not None:
        frame_queue = queues.get(core_id)
    else:
        frame_queue = next(iter(queues.values()), None)  # 默认取第一个存在的队列

    if frame_queue is None:
        logger.error(f"Core {core_id} not found")
        return

    while True:
        frame = frame_queue.get()
        image = np.frombuffer(frame.frame_bytes, np.uint8).reshape((720, 1280, 3))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        _, buffer = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'


@debug.get('/video_stream')
async def video_stream():
    return StreamingResponse(generate_frames(None), media_type='multipart/x-mixed-replace; boundary=frame')


@debug.get('/video_stream/{core_id}')
async def video_stream(core_id: str):
    return StreamingResponse(generate_frames(core_id), media_type='multipart/x-mixed-replace; boundary=frame')
