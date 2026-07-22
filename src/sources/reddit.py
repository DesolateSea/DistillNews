import os, praw, json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

REDDIT_SECRET = os.getenv("REDDIT_SECRET")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_SECRET,
    user_agent='praw'
)


indian_subreddits = [
    'india',
    'IndiaSpeaks',
    'unitedstatesofindia',
    'worldnews',
    'indianews',
    'IndiaCricket',
    'Cricket',
    'indiadiscussion',
    'GeopoliticsIndia',
    'IndiaTech',
    'developersIndia',
    'IndiaInvestments',
    'IndianStreetBets',
    'news',
    'UpliftingNews',
    'InternationalNews',
    'politics',
    'GlobalNews',
    'CryptoNews',
    'sports',
    'soccer',
    'nba',
    'nfl',
    'science',
    'artificial'
]

def fetch_recent_posts(subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    recent_posts = []
    for submission in subreddit.top(time_filter="day"):
            recent_posts.append(submission)
    return recent_posts

def extract_media(submission):
    media = []

    # Direct image or video in the URL
    if submission.url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.webm')):
        media.append(submission.url)

    # Reddit-hosted video
    if submission.is_video and submission.media:
        reddit_video = submission.media.get("reddit_video", {})
        if "fallback_url" in reddit_video:
            media.append(reddit_video["fallback_url"])

    # Reddit image gallery
    if hasattr(submission, "is_gallery") and submission.is_gallery:
        if hasattr(submission, "media_metadata"):
            for item in submission.media_metadata.values():
                if item["status"] == "valid":
                    media_url = item["s"].get("u", "").replace("&amp;", "&")
                    media.append(media_url)

    # Preview images (if no gallery or video)
    if hasattr(submission, "preview"):
        images = submission.preview.get("images", [])
        for img in images:
            if "source" in img:
                media_url = img["source"]["url"].replace("&amp;", "&")
                if media_url not in media:
                    media.append(media_url)

    return media


news_posts = []
# will use julep here
def is_news_post(title, tags):
    return True

cur_date = datetime.now().strftime("%Y-%m-%d")
output_dir = f'api_data/reddit/{cur_date}'
os.makedirs(output_dir, exist_ok=True)

for subreddit in indian_subreddits:
    posts = fetch_recent_posts(subreddit)
    for post in posts:
        tags = [post.link_flair_text] if post.link_flair_text else []
        if is_news_post(post.title, tags):
            news_post = {
                'title': post.title,
                'url': post.url,
                'created_utc': post.created_utc,
                'subreddit': post.subreddit.display_name,
                'media': extract_media(post),
                'content': post.selftext.strip() if post.selftext else "",
                'score': post.score
            }
            news_posts.append(news_post)
    with open(f'api_data/reddit/{cur_date}/{subreddit}.json', 'w+') as f:
        json.dump(news_posts, f, indent=4)
