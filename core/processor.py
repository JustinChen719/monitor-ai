import threading
import time

from core.shared_buffer import SharedMemoryManager, Frame
from utils import get_logger, get_config

logger = get_logger(__name__)
config = get_config()


class SampledFrame:
    def __init__(self, core_id: str, frame: Frame):
        self.core_id = core_id
        self.frame = frame


class Processor:
    def __init__(
            self,
            frame_memory_manager: SharedMemoryManager,
            display_memory_manager: SharedMemoryManager = None,
            process_frequency: int = 30
    ):
        '''
        处理器，对拉流过来的视频帧进行采样、AI处理。
        :param frame_memory_manager: 拉流原始数据
        :param display_memory_manager: 用于debug演示处理效果
        # :param sample_frequency: 采样频率，理论每秒采样多少次
        :param process_frequency: 处理频率，理论每秒处理多少次
        '''
        self._frame_memory_manager = frame_memory_manager
        self._display_memory_manager = display_memory_manager

        # 采样的帧
        self._sampled_frames: list[SampledFrame] = []

        # 执行间隔
        self._process_interval = 1 / process_frequency

        # 执行线程
        self._thread = None
        self._stop = threading.Event()

    def _process(self):
        for sampled_frame in self._sampled_frames:
            if config.debug:
                self._display_memory_manager.get_buffer(sampled_frame.core_id).write_frame(sampled_frame.frame)
            # time.sleep(self._process_interval)

    def _sample(self):
        self._sampled_frames.clear()
        for core_id, buffer in self._frame_memory_manager.get_all_buffers().items():
            # logger.info(buffer.get_frame_count())
            frame = buffer.read_frame()
            if frame is None:
                continue
            self._sampled_frames.append(SampledFrame(core_id, frame))

            # time.sleep(self._sample_interval)

    def _run(self):
        while not self._stop.is_set():
            time.sleep(self._process_interval)
            try:
                self._sample()
                self._process()
            except Exception as e:
                time.sleep(self._process_interval)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self._thread = None
