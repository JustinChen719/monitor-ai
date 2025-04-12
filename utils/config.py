import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.debug = bool(os.getenv("DEBUG", False))
        self.api_port = int(os.getenv("API_PORT", 8000))
        self.video_output = os.getenv("VIDEO_OUTPUT")
        self.executable = os.getenv("FFMPEG_EXECUTABLE")
        self.stream_server_url = os.getenv("STREAM_SERVER_URL")

        self._check()

    def _check(self):
        if self.video_output is None:
            raise ValueError("VIDEO_OUTPUT is not set")
        if self.executable is None:
            raise ValueError("FFMPEG_EXECUTABLE is not set")
        if self.stream_server_url is None:
            raise ValueError("STREAM_SERVER_URL is not set")
