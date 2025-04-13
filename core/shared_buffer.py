from multiprocessing.shared_memory import SharedMemory
from multiprocessing import Lock

import numpy as np


class Frame:
    def __init__(self, frame_bytes: bytes, video_width: int, video_height: int, timestamp: int):
        self.frame_bytes = frame_bytes
        self.video_width = video_width
        self.video_height = video_height
        self.timestamp = timestamp

    def __len__(self):
        return len(self.frame_bytes) + 8

    def to_bytes(self):
        # video_width 和 video_height 可以不参与编解码，因为在对应的 SharedRingBuffer 会静态配置
        return self.frame_bytes + self.timestamp.to_bytes(8)

    @classmethod
    def from_bytes(cls, data: bytes, video_width: int, video_height: int):
        frame_bytes = data[:-8]
        timestamp = int.from_bytes(data[-8:])
        return cls(frame_bytes, video_width, video_height, timestamp)


class SharedRingBuffer:
    def __init__(self, video_width: int, video_height: int, num_slots=10):
        self.video_width = video_width
        self.video_height = video_height
        self.num_slots = num_slots

        self.frame_size = video_width * video_height * 3 + 8
        self.total_size = self.frame_size * num_slots
        self.shm = SharedMemory(create=True, size=self.total_size)
        self.buffer = np.ndarray(
                (num_slots, self.frame_size),
                dtype=np.uint8,
                buffer=self.shm.buf
        )

        # 读写指针
        self.read_pos = 0
        self.write_pos = 0
        self.lock = Lock()

    def write_frame(self, frame: Frame) -> None:
        with self.lock:
            self.buffer[self.write_pos] = np.frombuffer(frame.to_bytes(), dtype=np.uint8)
            self.write_pos = (self.write_pos + 1) % self.num_slots

            # 如果写指针追上读指针，则读指针后移一位
            if self.read_pos == self.write_pos:
                self.read_pos = (self.read_pos + 1) % self.num_slots

    def read_frame(self) -> Frame | None:
        with self.lock:
            if self.read_pos == self.write_pos:
                return None

            frame = Frame.from_bytes(self.buffer[self.read_pos].tobytes(), self.video_width, self.video_height)
            self.read_pos = (self.read_pos + 1) % self.num_slots
            return frame

    def clear(self):
        with self.lock:
            self.read_pos = 0
            self.write_pos = 0

    def get_frame_count(self) -> int:
        with self.lock:
            return (self.write_pos - self.read_pos + self.num_slots) % self.num_slots

    def close(self):
        with self.lock:
            self.shm.close()
            self.shm.unlink()


class SharedMemoryManager:
    def __init__(self):
        self.buffers: dict[str, SharedRingBuffer] = {}

    def create_buffer(self, core_id: str, video_width: int, video_height: int, num_slots: int = 10):
        self.buffers[core_id] = SharedRingBuffer(video_width, video_height, num_slots)
        return self.buffers[core_id]

    def get_buffer(self, core_id: str) -> SharedRingBuffer:
        return self.buffers.get(core_id)

    def get_all_buffers(self) -> dict[str, SharedRingBuffer]:
        return self.buffers

    def remove_buffer(self, core_id: str):
        temp_buffer = self.buffers.pop(core_id, None)
        if temp_buffer:
            temp_buffer.close()
            del temp_buffer
            return True
