import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import instaloader
import requests

from config import DOWNLOAD_ROOT, MAX_WORKERS
from validators import sanitize_filename

logger = logging.getLogger(__name__)


class InstagramDownloader:
    def __init__(
        self,
        max_workers: int = MAX_WORKERS,
        progress_callback: Optional[Callable[[str], None]] = None,
        transcribe_fn: Optional[Callable[[str], Optional[str]]] = None,
    ):
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_comments=False,
            save_metadata=False,
        )
        self.max_workers = max_workers
        self.progress_callback = progress_callback or (lambda msg: None)
        self.transcribe_fn = transcribe_fn

    def _emit(self, msg: str):
        self.progress_callback(msg)
        logger.info(msg)

    def _build_user_dirs(self, username: str) -> dict[str, Path]:
        safe_user = sanitize_filename(username)
        base = DOWNLOAD_ROOT / safe_user
        dirs = {}
        for name in ("images", "videos", "captions", "metadata", "transcripts"):
            d = base / name
            d.mkdir(parents=True, exist_ok=True)
            dirs[name] = d
        return dirs

    def _download_file(self, url: str, dest: Path) -> bool:
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            logger.error("Failed to download %s: %s", url, e)
            return False

    def _save_caption(self, dirs: dict[str, Path], shortcode: str, caption: Optional[str]):
        if caption:
            (dirs["captions"] / f"{shortcode}.txt").write_text(caption, encoding="utf-8")

    def _save_metadata(self, dirs: dict[str, Path], post):
        meta = {
            "shortcode": post.shortcode,
            "owner": post.owner_username,
            "date": post.date_utc.isoformat(),
            "typename": post.typename,
            "likes": post.likes,
            "comments": post.comments,
            "caption": post.caption or "",
            "url": f"https://www.instagram.com/p/{post.shortcode}/",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        (dirs["metadata"] / f"{post.shortcode}.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _transcribe_video(self, video_path: Path, dirs: dict[str, Path], shortcode: str):
        if not self.transcribe_fn:
            return
        try:
            text = self.transcribe_fn(str(video_path))
            if text:
                (dirs["transcripts"] / f"{shortcode}.txt").write_text(text, encoding="utf-8")
                self._emit(f"  Transcribed: {video_path.name}")
        except Exception as e:
            logger.error("Transcription failed for %s: %s", video_path, e)

    def _download_media(self, dirs: dict[str, Path], shortcode: str, url: str, name: str) -> Optional[Path]:
        is_video = "mp4" in url.split("?")[0]
        ext = "mp4" if is_video else "jpg"
        folder = dirs["videos"] if is_video else dirs["images"]
        dest = folder / f"{shortcode}_{name}.{ext}"
        if self._download_file(url, dest):
            return dest
        return None

    def _process_post(self, post, dirs: dict[str, Path]) -> dict:
        shortcode = post.shortcode
        self._emit(f"Processing: {shortcode} ({post.typename})")

        self._save_caption(dirs, shortcode, post.caption)
        self._save_metadata(dirs, post)

        media_count = 0
        video_paths = []

        if post.typename == "GraphSidecar":
            for i, node in enumerate(post.get_sidecar_nodes(), start=1):
                if node.is_video:
                    path = self._download_media(dirs, shortcode, node.video_url, f"media_{i}")
                    if path:
                        media_count += 1
                        video_paths.append(path)
                else:
                    path = self._download_media(dirs, shortcode, node.display_url, f"media_{i}")
                    if path:
                        media_count += 1
        elif post.typename == "GraphVideo":
            path = self._download_media(dirs, shortcode, post.video_url, "media")
            if path:
                media_count += 1
                video_paths.append(path)
        else:
            path = self._download_media(dirs, shortcode, post.url, "media")
            if path:
                media_count += 1

        for vp in video_paths:
            self._transcribe_video(vp, dirs, shortcode)

        return {
            "shortcode": shortcode,
            "typename": post.typename,
            "media_count": media_count,
            "videos_transcribed": len(video_paths),
        }

    def download_profile(self, username: str) -> dict:
        self._emit(f"Loading profile: {username}")
        profile = instaloader.Profile.from_username(self.loader.context, username)
        posts = list(profile.get_posts())
        total = len(posts)
        self._emit(f"Found {total} posts for @{username}")

        dirs = self._build_user_dirs(username)

        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_post, p, dirs): p for p in posts}
            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    post = futures[future]
                    logger.error("Failed to process post %s: %s", post.shortcode, e)
                    results.append({"shortcode": post.shortcode, "error": str(e)})
                self._emit(f"Progress: {completed}/{total}")

        total_media = sum(r.get("media_count", 0) for r in results)
        errors = sum(1 for r in results if "error" in r)
        self._emit(f"Done! {total_media} media files from {total} posts ({errors} errors)")

        return {
            "username": username,
            "total_posts": total,
            "total_media": total_media,
            "errors": errors,
            "posts": results,
        }
