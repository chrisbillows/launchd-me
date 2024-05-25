import logging
import os
import platform
from pathlib import Path


def get_log_path(app_name: str = "launchd-me") -> Path:
    home = Path.home()
    if platform.system() == "Windows":
        log_path = Path(os.getenv("APPDATA", home)) / app_name / "logs"
    elif platform.system() == "Darwin":
        log_path = home / "Library" / "Logs" / app_name
    else:  # Linux
        log_path = home / ".local" / "share" / app_name / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def setup_logger(log_path: Path, app_name: str = "launchd-me"):
    log_file_path = log_path / "app.log"
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


log_path = get_log_path()
logger = setup_logger(log_path)
logger.debug(f"Log directory and logger have been configured for {logger.name}")
