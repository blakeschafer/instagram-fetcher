import re
from urllib.parse import urlparse

USERNAME_RE = re.compile(r"^[a-zA-Z0-9._]{1,30}$")
SAFE_FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def extract_username(text: str) -> str:
    text = text.strip()
    if "instagram.com" in text:
        parsed = urlparse(text)
        if parsed.hostname and parsed.hostname.endswith("instagram.com"):
            parts = parsed.path.strip("/").split("/")
            if parts and parts[0]:
                return parts[0]
        raise ValueError("Could not extract username from URL")
    return text


def validate_username(username: str) -> str:
    username = extract_username(username)
    if not USERNAME_RE.match(username):
        raise ValueError("Invalid username: only letters, numbers, periods, and underscores allowed (max 30 chars)")
    return username


def sanitize_filename(name: str) -> str:
    sanitized = SAFE_FILENAME_RE.sub("_", name)
    sanitized = sanitized.strip("._")
    if not sanitized:
        sanitized = "unnamed"
    return sanitized[:255]
