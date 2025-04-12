import uvicorn
from fastapi import FastAPI

from core import get_stream_controller
from utils import get_logger, get_config
from api import router

app = FastAPI()
app.include_router(router)
logger = get_logger()

if __name__ == "__main__":
    config = get_config()
    stream_controller = get_stream_controller()

    logger.info(f"Server started at {config.api_port}")
    uvicorn.run(app, host="localhost", port=config.api_port)
