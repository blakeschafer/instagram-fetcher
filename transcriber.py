import logging
import subprocess
from pathlib import Path
from typing import Optional

from config import WHISPER_MODEL

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper
        logger.info("Loading Whisper model: %s", WHISPER_MODEL)
        _model = whisper.load_model(WHISPER_MODEL)
    return _model


def extract_audio(video_path: str) -> str:
    wav_path = str(Path(video_path).with_suffix(".wav"))
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-ar", "16000", "-ac", "1", "-f", "wav", wav_path,
        ],
        capture_output=True,
        check=True,
    )
    return wav_path


def transcribe_video(video_path: str) -> Optional[str]:
    wav_path = None
    try:
        wav_path = extract_audio(video_path)
        model = _get_model()
        result = model.transcribe(wav_path)
        text = result.get("text", "").strip()
        return text if text else None
    except FileNotFoundError:
        logger.error("ffmpeg not found — install ffmpeg for transcription support")
        return None
    except Exception as e:
        logger.error("Transcription error for %s: %s", video_path, e)
        return None
    finally:
        if wav_path:
            Path(wav_path).unlink(missing_ok=True)
