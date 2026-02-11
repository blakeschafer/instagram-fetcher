## Instagram Fetcher

Download images, videos, captions, metadata, and transcripts from public Instagram profiles.

Features:

* Web UI with real-time progress (SSE)
* Parallel downloads
* Captions, metadata (JSON), and video transcription (Whisper)
* Rate limiting and input validation
* Docker support

---

### Setup (local)

Clone:

```
git clone <repo>
cd instagram-fetcher
```

Install:

```
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust settings:

```
cp .env.example .env
```

Run:

```
python app.py
```

Open http://localhost:5000 in your browser.

---

### Docker

Build:

```
docker build -t insta-fetcher .
```

Run:

```
docker run -p 5000:5000 insta-fetcher
```

---

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DOWNLOAD_ROOT` | `./downloads/instagram` | Where media is saved |
| `MAX_WORKERS` | `5` | Parallel download threads |
| `WHISPER_MODEL` | `base` | Whisper model size (tiny/base/small/medium/large) |
| `ENABLE_TRANSCRIPTION` | `true` | Enable video transcription |
| `SECRET_KEY` | random | Flask secret key |
| `FLASK_PORT` | `5000` | Server port |
| `RATE_LIMIT_DOWNLOAD` | `3/minute` | Rate limit on download endpoint |

---

### Output Structure

```
downloads/instagram/{username}/posts/{shortcode}/
  media.jpg          # or media.mp4 for videos
  media_1.jpg        # carousel items numbered
  caption.txt        # post caption
  metadata.json      # likes, comments, date, etc.
  transcript.txt     # video transcription (if enabled)
```

---

### Notes

* Public accounts only
* Heavy scraping may trigger Instagram rate limits
* Transcription requires ffmpeg installed locally (included in Docker image)
* For private accounts use Instaloader login

---
