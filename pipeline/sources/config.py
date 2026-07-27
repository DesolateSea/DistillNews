"""Configuration queries, categories, subreddits, and topics for pipeline sources."""

GNEWS_QUERIES: list[str] = [
    "indian economy",
    "india government policy",
    "india health",
    "india news",
    "india social news",
    "india technology science",
    "india travel culture",
]

MEDIA_STACK_CATEGORIES: list[str] = [
    "general",
    "business",
    "entertainment",
    "health",
    "science",
    "sports",
    "technology",
]

RAPID_NEWS_SECTIONS: list[str] = [
    "WORLD",
    "NATIONAL",
    "BUSINESS",
    "TECHNOLOGY",
    "ENTERTAINMENT",
    "SPORTS",
    "SCIENCE",
    "HEALTH",
]

SUBREDDITS: list[str] = [
    "india",
    "IndiaSpeaks",
    "unitedstatesofindia",
    "worldnews",
    "indianews",
    "IndiaCricket",
    "Cricket",
    "indiadiscussion",
    "GeopoliticsIndia",
    "IndiaTech",
    "developersIndia",
    "IndiaInvestments",
    "IndianStreetBets",
    "news",
    "UpliftingNews",
    "InternationalNews",
    "politics",
    "GlobalNews",
    "CryptoNews",
    "sports",
    "soccer",
    "nba",
    "nfl",
    "science",
    "artificial",
]

NEWS_ORG_TOPICS: dict[str, str] = {
    "government_policy": "india government policy",
    "markets_crypto": "india crypto market",
    "business_finance": "indian economy",
    "national_international_news": "india news",
    "tech_science_innovation": "india technology science",
    "health_medicine": "india health",
    "sports": "india sports",
    "travel_lifestyle_culture": "india travel culture",
    "regional_news": "india regional news",
    "community_social_news": "india social news",
    "fact_checking": "india fact checking",
}

CORE_KEYWORDS: list[str] = [
    "Artificial intelligence",
    "Computer science",
    "Technology",
    "Machine learning",
    "Physics",
    "Biology",
    "Chemistry",
    "Mathematics",
    "Bio technology",
    "Finance",
    "Cryptography",
    "Network",
    "Statistics",
    "Economics",
]
