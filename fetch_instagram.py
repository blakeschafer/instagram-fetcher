import instaloader
import sys
from urllib.parse import urlparse

def extract_username(url_or_name):
    if "instagram.com" in url_or_name:
        path = urlparse(url_or_name).path.strip("/")
        return path.split("/")[0]
    return url_or_name

def download_profile(profile_input):
    username = extract_username(profile_input)

    L = instaloader.Instaloader(
        download_pictures=True,
        download_videos=True,
        download_video_thumbnails=False,
        download_comments=True,
        save_metadata=True,
        post_metadata_txt_pattern="{caption}",
        dirname_pattern="downloads/{profile}",
        filename_pattern="{date_utc}_UTC"
    )

    print(f"Fetching profile: {username}")
    profile = instaloader.Profile.from_username(L.context, username)

    L.download_profile(profile, profile_pic=True, fast_update=False)

    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_instagram.py <profile_url_or_username>")
        sys.exit(1)

    download_profile(sys.argv[1])
