import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Queue

from flask import Flask, Response, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

import config
from downloader import InstagramDownloader
from transcriber import transcribe_video
from validators import validate_username

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[config.RATE_LIMIT_DEFAULT],
    storage_uri="memory://",
)


@dataclass
class JobState:
    queue: Queue = field(default_factory=Queue)
    status: str = "running"
    result: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


jobs: dict[str, JobState] = {}
jobs_lock = threading.Lock()


def cleanup_stale_jobs():
    now = time.time()
    with jobs_lock:
        stale = [jid for jid, js in jobs.items() if now - js.created_at > config.JOB_TTL_SECONDS]
        for jid in stale:
            del jobs[jid]


def run_download_job(job_id: str, username: str):
    job = jobs[job_id]

    def progress_cb(msg: str):
        job.queue.put(("message", msg))

    transcribe_fn = transcribe_video if config.ENABLE_TRANSCRIPTION else None

    try:
        dl = InstagramDownloader(
            progress_callback=progress_cb,
            transcribe_fn=transcribe_fn,
        )
        result = dl.download_profile(username)
        job.result = result
        job.status = "done"
        job.queue.put(("done", json.dumps(result, indent=2)))
    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e)
        job.status = "error"
        job.queue.put(("error_event", "Download failed. Check the username and try again."))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
@limiter.limit(config.RATE_LIMIT_DOWNLOAD)
def download():
    data = request.get_json(silent=True) or {}
    raw = data.get("username", "").strip()

    if not raw:
        return jsonify({"error": "Username is required"}), 400

    try:
        username = validate_username(raw)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    cleanup_stale_jobs()

    job_id = uuid.uuid4().hex[:12]
    job = JobState()
    with jobs_lock:
        jobs[job_id] = job

    threading.Thread(target=run_download_job, args=(job_id, username), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/progress/<job_id>")
def progress(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    def stream():
        while True:
            try:
                event_type, data = job.queue.get(timeout=30)
            except Exception:
                yield "data: heartbeat\n\n"
                continue

            if event_type == "message":
                yield f"data: {data}\n\n"
            elif event_type == "done":
                yield f"event: done\ndata: {data}\n\n"
                return
            elif event_type == "error_event":
                yield f"event: error_event\ndata: {data}\n\n"
                return

    return Response(stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@app.route("/downloads")
def list_downloads():
    root = config.DOWNLOAD_ROOT
    if not root.exists():
        return jsonify([])
    profiles = []
    for user_dir in sorted(root.iterdir()):
        if user_dir.is_dir():
            images_dir = user_dir / "images"
            post_count = len(list(images_dir.iterdir())) if images_dir.exists() else 0
            profiles.append({"username": user_dir.name, "posts": post_count})
    return jsonify(profiles)


if __name__ == "__main__":
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
