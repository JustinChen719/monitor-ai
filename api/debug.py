import time
import cv2
import numpy as np

from starlette.responses import StreamingResponse, Response
from fastapi import APIRouter

from core import get_stream_controller
from core.shared_buffer import SharedRingBuffer
from utils import get_logger

logger = get_logger(__name__)

debug = APIRouter(prefix="/debug")


def generate_frames(core_id: str | None):
    stream_controller = get_stream_controller()
    buffers = stream_controller.display_memory_manager.get_all_buffers()
    if core_id is not None:
        buffer: SharedRingBuffer | None = buffers.get(core_id)
    else:
        buffer: SharedRingBuffer | None = next(iter(buffers.values()), None)  # 默认取第一个存在的队列

    if buffer is None:
        logger.error(f"Core {core_id} not found")
        return

    cnt, now, past, current_fps = 0, 0, 0, 0
    while True:
        frame = buffer.read_frame()
        if frame is None:
            time.sleep(0.05)
            continue
        cnt += 1

        image = np.frombuffer(frame.frame_bytes, np.uint8).reshape((frame.video_height, frame.video_width, 3))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 计算FPS
        if cnt != 0 and cnt % 20 == 0:
            now = time.time()
            current_fps = 20 / (now - past)
            # logger.debug(f"FPS: {current_fps:.1f}")
            past = now

        # 绘制到图像上
        text = f"FPS: {current_fps:.2f}"
        cv2.putText(
                image,
                text,
                org=(10, 70),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=0.5,
                color=(255, 255, 255),
                thickness=2,
                lineType=cv2.LINE_AA
        )

        # 编码并输出图像
        _, data = cv2.imencode('.jpg', image)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + data.tobytes() + b'\r\n')


@debug.get('/video_stream')
async def video_stream():
    return StreamingResponse(generate_frames(None), media_type='multipart/x-mixed-replace; boundary=frame')


@debug.get('/video_stream/{core_id}')
async def video_stream(core_id: str):
    return StreamingResponse(generate_frames(core_id), media_type='multipart/x-mixed-replace; boundary=frame')
