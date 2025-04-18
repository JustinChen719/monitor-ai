import subprocess
import threading
import time

from ffmpy3 import FFmpeg
from dataclasses import dataclass

from core.shared_buffer import SharedRingBuffer, Frame
from utils import get_logger

logger = get_logger(__name__)


@dataclass
class FFmpegConfig:
    executable: str = "ffmpeg"
    inputs: dict[str, list] = None
    outputs: dict[str, list] = None


@dataclass
class StreamCoreConfig:
    core_id: str  # 唯一标识符
    ip: str  # 推流源的 ip
    ffmpeg_config: FFmpegConfig  # ffmpeg 配置
    frame_buffer: SharedRingBuffer  # 拉流提取缓冲区

    # 流视频参数
    video_width: int = 640
    video_height: int = 360
    bytes_per_pixel: int = 3


@dataclass
class StreamCoreStatus:
    core_id: str
    ip: str
    is_running: bool
    video_width: int
    video_height: int


class StreamCore:
    def __init__(self, config: StreamCoreConfig):
        self.core_id: str = config.core_id
        self.ip: str = config.ip
        self.ffmpeg_config: FFmpegConfig = config.ffmpeg_config
        self.frame_buffer: SharedRingBuffer = config.frame_buffer

        # ffmpeg配置 和 子进程
        self.ffmpeg: FFmpeg = FFmpeg(
                executable=self.ffmpeg_config.executable,
                inputs=self.ffmpeg_config.inputs,
                outputs=self.ffmpeg_config.outputs
        )
        self.process: subprocess.Popen | None = None

        # 当前执行线程
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
        '''
        实例线程执行函数
        '''
        try:
            cmd = self.ffmpeg.cmd
            self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
            )
            logger.info(f"核心: {self.core_id},开始监听推流源: {self.ip}")
            logger.info(f"FFmpeg 命令: {cmd}")

            if self.process.stderr:
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

                self.frame_buffer.write_frame(Frame(frame_data, self.video_width, self.video_height, int(time.time() * 1000)))
                # logger.info(f"核心 {self.core_id} 推流帧: {int(time.time() * 1000)}")

            self.process.stdout.close()
            self.process.terminate()
            self.process.wait()
        except Exception as e:
            logger.error(f"核心 {self.core_id} 错误: {e}")
        finally:
            logger.info(f"核心 {self.core_id} 终止")

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

    def get_status(self) -> StreamCoreStatus:
        return StreamCoreStatus(
                core_id=self.core_id,
                ip=self.ip,
                is_running=self.thread and self.thread.is_alive(),
                video_width=self.video_width,
                video_height=self.video_height
        )
