import time
from queue import Queue

import numpy as np


class Frame:
    def __init__(self, frame_bytes: bytes, video_width: int, video_height: int, ):
        # self.frame = np.frombuffer(frame_bytes, dtype=np.uint8).reshape((video_height, video_width, 3))
        self.frame_bytes = frame_bytes
        self.timestamp = int(time.time() * 1000)


class FrameQueues:
    def __init__(self):
        self._queues: dict[str, Queue[Frame]] = {}

    def add_queue(self, key: str, maxsize: int = 10) -> Queue[Frame]:
        if key not in self._queues:
            self._queues[key] = Queue(maxsize=maxsize)
        return self._queues[key]

    def get_queue(self, key: str) -> Queue[Frame] | None:
        return self._queues.get(key, None)

    def get_all_queues(self) -> dict[str, Queue[Frame]]:
        return self._queues

    def remove_queue(self, key: str) -> bool:
        if key in self._queues:
            del self._queues[key]
            return True
        return False

    def has_queue(self, key: str) -> bool:
        return key in self._queues

    def clear_all(self):
        self._queues.clear()
