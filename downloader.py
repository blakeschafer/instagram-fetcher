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

    def _build_post_dir(self, username: str, shortcode: str) -> Path:
        safe_user = sanitize_filename(username)
        safe_code = sanitize_filename(shortcode)
        post_dir = DOWNLOAD_ROOT / safe_user / "posts" / safe_code
        post_dir.mkdir(parents=True, exist_ok=True)
        return post_dir

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

    def _save_caption(self, post_dir: Path, caption: Optional[str]):
        if caption:
            (post_dir / "caption.txt").write_text(caption, encoding="utf-8")

    def _save_metadata(self, post_dir: Path, post):
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
        (post_dir / "metadata.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _transcribe_video(self, video_path: Path, post_dir: Path):
        if not self.transcribe_fn:
            return
        try:
            text = self.transcribe_fn(str(video_path))
            if text:
                (post_dir / "transcript.txt").write_text(text, encoding="utf-8")
                self._emit(f"  Transcribed: {video_path.name}")
        except Exception as e:
            logger.error("Transcription failed for %s: %s", video_path, e)

    def _download_media(self, post_dir: Path, url: str, name: str) -> Optional[Path]:
        ext = "mp4" if "mp4" in url.split("?")[0] else "jpg"
        dest = post_dir / f"{name}.{ext}"
        if self._download_file(url, dest):
            return dest
        return None

    def _process_post(self, post) -> dict:
        post_dir = self._build_post_dir(post.owner_username, post.shortcode)
        self._emit(f"Processing: {post.shortcode} ({post.typename})")

        self._save_caption(post_dir, post.caption)
        self._save_metadata(post_dir, post)

        media_count = 0
        video_paths = []

        if post.typename == "GraphSidecar":
            for i, node in enumerate(post.get_sidecar_nodes(), start=1):
                if node.is_video:
                    path = self._download_media(post_dir, node.video_url, f"media_{i}")
                    if path:
                        media_count += 1
                        video_paths.append(path)
                else:
                    path = self._download_media(post_dir, node.display_url, f"media_{i}")
                    if path:
                        media_count += 1
        elif post.typename == "GraphVideo":
            path = self._download_media(post_dir, post.video_url, "media")
            if path:
                media_count += 1
                video_paths.append(path)
        else:
            path = self._download_media(post_dir, post.url, "media")
            if path:
                media_count += 1

        for vp in video_paths:
            self._transcribe_video(vp, post_dir)

        return {
            "shortcode": post.shortcode,
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

        results = []
        completed = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_post, p): p for p in posts}
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
