import threading
import av

from datetime import datetime
from av.container import InputContainer
from onvif import ONVIFCamera
from dataclasses import dataclass

from core.shared_buffer import SharedRingBuffer, Frame
from utils import get_logger

logger = get_logger(__name__)


# @dataclass
# class FFmpegConfig:
#     executable: str = "ffmpeg"
#     inputs: dict[str, list] = None
#     outputs: dict[str, list] = None


@dataclass
class StreamCoreConfig:
    core_id: str  # 唯一标识符
    username: str
    password: str
    ip: str
    port: int
    path: str

    frame_buffer: SharedRingBuffer  # 拉流提取缓冲区

    # 流视频参数
    video_width: int = 640
    video_height: int = 360
    bytes_per_pixel: int = 3


@dataclass
class StreamCoreStatus:
    core_id: str
    ip: str
    video_width: int
    video_height: int
    bytes_per_pixel: int

    is_running: bool


class StreamCore:
    def __init__(self, config: StreamCoreConfig):
        self.core_id: str = config.core_id
        self.username = config.username
        self.password = config.password
        self.ip = config.ip
        self.port = config.port
        self.path = config.path
        self.frame_buffer: SharedRingBuffer = config.frame_buffer

        # Pyav实例
        self.device_time = 0
        self.container: InputContainer | None = None

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

    def _sync_device_time(self) -> None:
        try:
            cam = ONVIFCamera(self.ip, 80, "", "")
            service = cam.create_devicemgmt_service()
            device_local_time = service.GetSystemDateAndTime()["LocalDateTime"]
            dt = datetime(
                    year=device_local_time['Date']['Year'],
                    month=device_local_time['Date']['Month'],
                    day=device_local_time['Date']['Day'],
                    hour=device_local_time['Time']['Hour'],
                    minute=device_local_time['Time']['Minute'],
                    second=device_local_time['Time']['Second'],
            )
            self.device_time = int(dt.timestamp() * 1000)
        except Exception as e:
            logger.error(f"同步设备时间错误: {e}")

    def _run(self):
        '''
        实例线程执行函数
        '''
        try:
            logger.info(f"核心: {self.core_id} 开始监听推流源: {self.ip}")
            rtsp_url = f"rtsp://{self.username}:{self.password}@{self.ip}:{self.port}{self.path}"
            self.container = av.open(
                    file=rtsp_url,
                    options={"rtsp_transport": "udp", "stimeout": "5000000"},
                    timeout=5
            )
            stream = next(s for s in self.container.streams if s.type == "video")

            sync = False
            for video_frame in self.container.decode(stream):
                if self.stop_event.is_set():
                    break

                if not video_frame.pts:
                    continue

                if not sync:
                    sync = True
                    self._sync_device_time()

                image = video_frame.to_ndarray(format="bgr24")
                absolute_time = self.device_time + int(video_frame.pts * video_frame.time_base * 1000)
                frame = Frame(image.tobytes(), self.video_width, self.video_height, absolute_time)
                self.frame_buffer.write_frame(frame)

        except Exception as e:
            logger.error(f"核心 {self.core_id} 错误: {e}")
        finally:
            self.container = None
            logger.info(f"核心 {self.core_id} 推流源: {self.ip} 停止")

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
            try:
                self.stop_event.set()
                if self.thread and self.thread.is_alive():
                    self.thread.join()
                    self.thread = None
            except Exception as e:
                logger.error(f"关闭推流源 {self.ip} 错误: {e}")

    def get_status(self) -> StreamCoreStatus:
        return StreamCoreStatus(
                core_id=self.core_id,
                ip=self.ip,
                video_width=self.video_width,
                video_height=self.video_height,
                bytes_per_pixel=self.bytes_per_pixel,
                is_running=self.thread and self.thread.is_alive(),
        )
