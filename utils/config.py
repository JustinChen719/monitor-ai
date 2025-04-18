import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        self.debug = bool(os.getenv("DEBUG", False))
        self.api_port = int(os.getenv("API_PORT", 8000))

        self.executable = os.getenv("FFMPEG_EXECUTABLE")
        self.stream_server_url = os.getenv("STREAM_SERVER_URL")

        self.process_frequency = int(os.getenv("PROCESS_FREQUENCY", 30))

        self._check()

    def _check(self):
        if self.executable is None:
            raise ValueError("FFMPEG_EXECUTABLE is not set")
        if self.stream_server_url is None:
            raise ValueError("STREAM_SERVER_URL is not set")
