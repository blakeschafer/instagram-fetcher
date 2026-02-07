import instaloader
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm


class InstagramDownloader:
    def __init__(self, max_workers=5):
        self.loader = instaloader.Instaloader(
            download_pictures=True,
            download_videos=True,
            download_comments=False,
            save_metadata=False
        )
        self.max_workers = max_workers

    def _download_post(self, post):
        self.loader.download_post(post, target=post.owner_username)

    def download_profile(self, username):
        profile = instaloader.Profile.from_username(self.loader.context, username)
        posts = list(profile.get_posts())

        print(f"Downloading {len(posts)} posts...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._download_post, p) for p in posts]

            for _ in tqdm(as_completed(futures), total=len(futures)):
                pass

        print("Done!")
