from uuid import uuid4

from core.shared_buffer import SharedMemoryManager
from core.processor import Processor
from utils import get_config, get_logger
from core.stream_core import StreamCore, StreamCoreConfig, StreamCoreStatus

logger = get_logger(__name__)


class StreamController:
    def __init__(self):
        self.config = get_config()
        self.cores: dict[str, StreamCore] = {}

        self.frame_memory_manager: SharedMemoryManager = SharedMemoryManager()
        self.display_memory_manager: SharedMemoryManager = SharedMemoryManager()

        # AI 处理
        self.processor = Processor(
                self.frame_memory_manager,
                self.display_memory_manager,
                process_frequency=self.config.process_frequency
        )
        self.processor.start()

    def create_core(
            self,
            username: str,
            password: str,
            ip: str,
            port: int = 554,
            path: str = "/Streaming/Channels/102",
            video_width: int = 640,
            video_height: int = 360,
            bytes_per_pixel: int = 3,
    ) -> str:
        '''
        创建core实例
        :param username:
        :param password:
        :param ip:
        :param port:
        :param path:
        :param video_width:
        :param video_height:
        :param bytes_per_pixel:
        :return: core_id
        '''
        # 查重
        for core_id, core in self.cores.items():
            if core.ip == ip:
                logger.warning(f"core {core_id} with ip {ip} already exists")
                core.start()
                return core_id

        core_id = str(uuid4())

        # 创建拉流buffer以及显示buffer
        frame_buffer = self.frame_memory_manager.create_buffer(core_id, video_width, video_height)
        self.display_memory_manager.create_buffer(core_id, video_width, video_height)

        # 创建core配置和实例
        core_config = StreamCoreConfig(
                core_id=core_id,
                username=username,
                password=password,
                ip=ip,
                port=port,
                path=path,
                frame_buffer=frame_buffer,
                video_width=video_width,
                video_height=video_height,
                bytes_per_pixel=bytes_per_pixel
        )
        self.cores[core_id] = StreamCore(core_config)
        self.cores[core_id].start()
        return core_id

    def start_core(self, core_id: str) -> bool:
        """
        启动指定实例
        """
        if core := self.cores.get(core_id):
            core.start()
            return True
        return False

    def stop_core(self, core_id: str) -> bool:
        """
        停止指定实例
        """
        if core := self.cores.get(core_id):
            core.stop()
            return True
        return False

    def delete_core(self, core_id: str) -> bool:
        """
        删除指定实例
        """
        if core := self.cores.get(core_id):
            core.stop()
            del self.cores[core_id]
            self.frame_memory_manager.remove_buffer(core_id)
            self.display_memory_manager.remove_buffer(core_id)
            return True
        return False

    # def enable_ai(self, core_id: str, enable_ai: bool) -> bool:
    #     """
    #     启停AI
    #     """
    #     if core := self.cores.get(core_id):
    #         core.enable_ai = enable_ai
    #         return True
    #     return False

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
