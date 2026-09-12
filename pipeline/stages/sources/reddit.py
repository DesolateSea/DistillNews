from pipeline.engine.stage import stage
from pipeline.engine.stream import RawArticle
from pipeline.engine.task import PipelineContext


@stage
def fetch_reddit(ctx: PipelineContext):
    """Fetch top posts from configured subreddits."""
    from config import config as default_config
    cfg = ctx.config if (ctx and ctx.config is not None) else default_config
    if not cfg.is_stage_enabled('fetch') or not cfg.is_source_enabled('reddit'):
        return
    
    from pipeline.sources.reddit import fetch_recent_posts, extract_media
    from pipeline.sources.config import SUBREDDITS
    
    for subreddit in SUBREDDITS:
        try:
            posts = fetch_recent_posts(subreddit)
        except Exception:
            continue
        for post in posts:
            news_post = {
                'title': post.title,
                'url': post.url,
                'created_utc': post.created_utc,
                'subreddit': post.subreddit.display_name,
                'media': extract_media(post),
                'content': post.selftext.strip() if post.selftext else '',
                'score': post.score,
                '_assured_news': False,
                '_prompt': 'news_from_reddit_post.prompt.md',
            }
            yield RawArticle(
                source='reddit',
                payload=news_post,
                url=post.url,
                title=post.title,
            )
