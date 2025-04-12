import subprocess
import threading
import time

from queue import Queue

import numpy as np
from ffmpy3 import FFmpeg
from dataclasses import dataclass

from core.frame_queues import Frame
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class FFmpegConfig:
    executable: str = "ffmpeg"
    inputs: dict[str, list] = None
    outputs: dict[str, list] = None


@dataclass
class StreamCoreConfig:
    core_id: str
    key: str
    ffmpeg_config: FFmpegConfig
    frame_queue: Queue

    video_width: int = 1280
    video_height: int = 720
    bytes_per_pixel: int = 3


class StreamCore:
    def __init__(self, config: StreamCoreConfig):
        self.core_id: str = config.core_id
        self.key: str = config.key
        self.ffmpeg_config: FFmpegConfig = config.ffmpeg_config
        self.frame_queue: Queue[Frame] = config.frame_queue  # 当前子线程的帧队列

        # ffmpeg 配置和 处理子线程
        self.ffmpeg: FFmpeg = FFmpeg(
                executable=self.ffmpeg_config.executable,
                inputs=self.ffmpeg_config.inputs,
                outputs=self.ffmpeg_config.outputs
        )
        self.process: subprocess.Popen | None = None

        # 线程安全
        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        # 视频参数
        self.video_width = config.video_width
        self.video_height = config.video_height
        self.bytes_per_pixel = config.bytes_per_pixel
        self.frame_size = self.video_width * self.video_height * self.bytes_per_pixel

        logger.info(f"处理核心 {self.core_id} 创建完成")

    def _run(self):
        try:
            cmd = self.ffmpeg.cmd
            logger.info(f"核心: {self.core_id},开始监听推流源: {self.key}")
            logger.info(f"FFmpeg 命令: {cmd}")
            self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
            )

            def _read_stderr():
                while True:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    logger.info(line.decode('utf-8').strip())

            threading.Thread(target=_read_stderr, daemon=True).start()

            while True:
                if self.stop_event.is_set() or self.process.poll() is not None:
                    break
                frame_data = self.process.stdout.read(self.frame_size)
                if not frame_data:
                    break
                if len(frame_data) != self.frame_size:
                    continue
                if self.frame_queue.full():
                    self.frame_queue.get(block=False)
                self.frame_queue.put(Frame(frame_data, self.video_width, self.video_height))
                # logger.info(f"核心 {self.core_id} 推流帧: {int(time.time() * 1000)}")

            self.process.stdout.close()
            self.process.terminate()
            self.process.wait()
        except Exception as e:
            logger.error(f"核心 {self.core_id} 错误: {e}")
        finally:
            logger.info(f"核心 {self.core_id} 停止")

    def start(self):
        '''
        启动：该函数是提供给主线程使用的
        '''
        with self.lock:
            if not self.thread or not self.thread.is_alive():
                self.stop_event.clear()
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()

    def stop(self):
        '''
        停止：该函数是提供给主线程使用的
        '''
        with self.lock:
            self.stop_event.set()
            if self.process:
                self.process.terminate()
            if self.thread and self.thread.is_alive():
                self.thread.join()
                self.thread = None

    def get_status(self):
        return {
            "core_id": self.core_id,
            "is_running": self.thread and self.thread.is_alive(),
        }
