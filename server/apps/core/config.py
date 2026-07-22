import os
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import config

DB_URL = config.DB_URL
JWT_SECRET = config.JWT_SECRET
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 15
CATEGORY=[
    "World", "Sports", "Technology", "Health", "Business","Science","Entertainment"
]
