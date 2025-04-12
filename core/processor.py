import threading
import time

from queue import Empty, Full

from core.frame_queues import FrameQueues, Frame
from utils import get_logger

logger = get_logger(__name__)


class SampledFrame:
    def __init__(self, core_id: str, frame: Frame):
        self.core_id = core_id
        self.frame = frame


class Processor:
    def __init__(self, frame_queues: FrameQueues, display_queues: FrameQueues = None):
        self._frame_queues = frame_queues
        self._sampled_frames: list[SampledFrame] = []  # 进过采样的帧

        self.display_mode = False if display_queues is None else True
        self._display_queues = display_queues

        self._thread = None
        self._stop = threading.Event()

    def _process(self):
        for sampled_frame in self._sampled_frames:
            if self.display_mode:
                try:
                    if self._display_queues.get_queue(sampled_frame.core_id).full():
                        self._display_queues.get_queue(sampled_frame.core_id).get(block=False)
                    self._display_queues.get_queue(sampled_frame.core_id).put(sampled_frame.frame, block=False)
                except Full:
                    pass
            time.sleep(0.05)

    def _sample(self):
        # 由于实时修改，可能会出现运行时错误: dictionary changed size during iteration

        self._sampled_frames.clear()
        for core_id, queue in self._frame_queues.get_all_queues().items():
            time.sleep(0.05)
            try:
                frame = queue.get(block=False)
                self._sampled_frames.append(SampledFrame(core_id, frame))
            except Empty:
                continue

    def _run(self):
        while not self._stop.is_set():
            try:
                self._sample()
                self._process()
            except Exception as e:
                time.sleep(0.01)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self._thread = None
