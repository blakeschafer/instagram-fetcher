## Instagram Fetcher

Download all images and videos from any public Instagram profile.

Features:

* Parallel downloads (faster)
* Progress bar
* Simple desktop GUI
* Docker support
* No browser automation required

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

Run:

```
python app.py
```

---

### Docker

Build:

```
docker build -t insta-fetcher .
```

Run:

```
docker run -it insta-fetcher
```

---

### Output

Media is saved to:

```
./<username>/
```

---

### Notes

* Public accounts only
* Heavy scraping may trigger Instagram rate limits
* For private accounts use Instaloader login

---
