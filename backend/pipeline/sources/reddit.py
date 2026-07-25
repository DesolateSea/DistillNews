import praw
from datetime import datetime
from config import config
from db import FileStore
from pipeline.sources.config import SUBREDDITS

from utils.logger import log

REDDIT_SECRET = config.REDDIT_SECRET
REDDIT_CLIENT_ID = config.REDDIT_CLIENT_ID

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_SECRET,
    user_agent="praw",
)


def fetch_recent_posts(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    recent_posts = []
    for submission in subreddit.top(time_filter="day"):
        recent_posts.append(submission)
    return recent_posts


def extract_media(submission):
    media = []

    if submission.url.endswith((".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webm")):
        media.append(submission.url)

    if submission.is_video and submission.media:
        reddit_video = submission.media.get("reddit_video", {})
        if "fallback_url" in reddit_video:
            media.append(reddit_video["fallback_url"])

    if hasattr(submission, "is_gallery") and submission.is_gallery:
        if hasattr(submission, "media_metadata"):
            for item in submission.media_metadata.values():
                if item["status"] == "valid":
                    media_url = item["s"].get("u", "").replace("&amp;", "&")
                    media.append(media_url)

    if hasattr(submission, "preview"):
        images = submission.preview.get("images", [])
        for img in images:
            if "source" in img:
                media_url = img["source"]["url"].replace("&amp;", "&")
                if media_url not in media:
                    media.append(media_url)

    return media


def run_reddit_ingestion():
    news_posts = []
    cur_date = datetime.now().strftime("%Y-%m-%d")

    for subreddit in SUBREDDITS:
        if log:
            log.fetch_start("Reddit", f"r/{subreddit}")
        posts = fetch_recent_posts(subreddit)
        for post in posts:
            tags = [post.link_flair_text] if post.link_flair_text else []
            news_post = {
                "title": post.title,
                "url": post.url,
                "created_utc": post.created_utc,
                "subreddit": post.subreddit.display_name,
                "media": extract_media(post),
                "content": post.selftext.strip() if post.selftext else "",
                "score": post.score,
            }
            news_posts.append(news_post)

        rel_path = f"api_data/reddit/{cur_date}/{subreddit}.json"
        FileStore.write_json(rel_path, news_posts)

        if log:
            log.fetch_done("Reddit", len(posts))


if __name__ == "__main__":
    run_reddit_ingestion()
