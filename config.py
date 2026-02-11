import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_ROOT = Path(os.getenv("DOWNLOAD_ROOT", str(BASE_DIR / "downloads" / "instagram")))

MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
ENABLE_TRANSCRIPTION = os.getenv("ENABLE_TRANSCRIPTION", "true").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "10/minute")
RATE_LIMIT_DOWNLOAD = os.getenv("RATE_LIMIT_DOWNLOAD", "3/minute")

JOB_TTL_SECONDS = int(os.getenv("JOB_TTL_SECONDS", "3600"))
