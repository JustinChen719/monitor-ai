import threading, os
import time

from datetime import datetime
from uuid import uuid4

from core.shared_buffer import SharedMemoryManager
from core.processor import Processor
from utils import get_config, get_logger
from core.stream_core import StreamCore, StreamCoreConfig, FFmpegConfig, StreamCoreStatus

logger = get_logger(__name__)


class StreamController:
    def __init__(self):
        self.config = get_config()
        self.cores: dict[str, StreamCore] = {}

        self.frame_memory_manager: SharedMemoryManager = SharedMemoryManager()
        self.display_memory_manager: SharedMemoryManager = SharedMemoryManager()

        # 视频输出目录
        self.video_output_dir = self.config.video_output
        if not os.path.exists(self.video_output_dir):
            os.makedirs(self.video_output_dir, exist_ok=True)

        # AI 处理
        self.processor = Processor(
                self.frame_memory_manager,
                self.display_memory_manager,
                process_frequency=self.config.process_frequency
        )
        self.processor.start()

    def create_core(
            self,
            key: str,
            video_width=1280,
            video_height=720,
            bytes_per_pixel=3,
    ) -> str:
        '''
        创建core实例
        :param key:
        :param video_width:
        :param video_height:
        :param bytes_per_pixel:
        :return: core_id
        '''
        # 查重
        for core_id, core in self.cores.items():
            if core.key == key:
                logger.warning(f"core {key} already exists")
                core.start()
                return core_id

        core_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4()}"
        output_dir = os.path.join(self.video_output_dir, core_id)
        os.makedirs(output_dir, exist_ok=True)

        # 创建拉流buffer以及显示buffer
        frame_buffer = self.frame_memory_manager.create_buffer(core_id, video_width, video_height)
        self.display_memory_manager.create_buffer(core_id, video_width, video_height)

        # 创建core配置和实例
        core_config = StreamCoreConfig(
                core_id=core_id,
                key=key,
                ffmpeg_config=FFmpegConfig(
                        executable=self.config.executable,
                        inputs={f"{self.config.stream_server_url}{key}": ["-listen", "1"]},
                        outputs={
                            # 分片 TS 文件
                            f"{output_dir}/output.m3u8": [  # HLS 播放列表
                                "-c", "copy",  # 直接拷贝编码，不转码
                                "-f", "hls",
                                "-hls_time", "10",  # 每个分片时长 10 秒
                                "-hls_list_size", "0",  # 保留所有分片（不限制数量）
                                "-hls_segment_filename", f"{output_dir}/segment_%03d.ts",  # 分片文件名格式
                                "-hls_flags", "delete_segments",  # 可选：自动清理旧分片（根据需求选择）
                                "-g", "250",  # 关键帧间隔（假设 25fps → 10 秒）
                                "-keyint_min", "250",
                                "-sc_threshold", "0"  # 强制按 GOP 分割分片
                            ],
                            # 管道输出
                            "pipe:1": [
                                "-f", "rawvideo",  # 格式：原始视频
                                "-pix_fmt", "rgb24",  # 像素格式
                                "-video_size", f"{video_width}x{video_height}"  # 分辨率
                            ]
                        }
                ),
                frame_buffer=frame_buffer,
                video_width=video_width,
                video_height=video_height,
                bytes_per_pixel=bytes_per_pixel
        )
        self.cores[core_id] = StreamCore(core_config)
        self.cores[core_id].start()
        return core_id

    def start_core(self, core_id: str) -> None:
        """
        启动指定实例
        """
        if core := self.cores.get(core_id):
            core.start()

    def stop_core(self, core_id: str) -> None:
        """
        停止指定实例
        """
        if core := self.cores.get(core_id):
            core.stop()

    def delete_core(self, core_id: str) -> None:
        """
        删除指定实例
        """
        if core := self.cores.get(core_id):
            core.stop()
            del self.cores[core_id]
            self.frame_memory_manager.remove_buffer(core_id)
            self.display_memory_manager.remove_buffer(core_id)

    def get_core_status(self, core_id: str) -> StreamCoreStatus | None:
        """
        获取实例状态
        """
        if core := self.cores.get(core_id):
            return core.get_status()
        return None

    def get_all_cores_status(self) -> list[StreamCoreStatus]:
        """
        获取所有实例状态
        """
        ret = []
        for core in self.cores.values():
            ret.append(core.get_status())
        return ret
