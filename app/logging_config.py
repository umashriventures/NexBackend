import sys
import logging
import os
from datetime import datetime
from loguru import logger
from fastapi import Request

# Create logs directory if not exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Custom log format
# <level> and </level> are loguru tags for coloring
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level> {extra}"
)

class InterceptHandler(logging.Handler):
    """
    Default handler from python logging to loguru.
    See: https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_logging():
    """
    Configures loguru to handle all logs (including standard logging)
    """
    # Remove default loguru handler
    logger.remove()

    # Add console handler
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level="INFO",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Add file handler with rotation and retention
    log_file = os.path.join(LOG_DIR, "nex_app_{time:YYYY-MM-DD}.log")
    logger.add(
        log_file,
        format=LOG_FORMAT,
        level="DEBUG",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    # Intercept standard logging (FastAPI, Uvicorn, etc.)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Specific configuration for other loggers
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    logger.info("Production-grade logging initialized successfully.")

# Middleware to add request_id to logs
async def logging_middleware(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    # Bind request_id to all logs in this request context
    with logger.contextualize(request_id=request_id):
        logger.info(f"Incoming request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.info(f"Completed request: {request.method} {request.url.path} - Status: {response.status_code}")
        return response
