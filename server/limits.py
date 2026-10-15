"""Shared fixed-window limits. Database failures fail closed."""
import hashlib
import time
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
from service.db.mongo import MongoHandle


async def limit_key(identity, action, maximum, seconds):
    window = int(time.time()) // seconds
    key = hashlib.sha256(f"{action}:{identity}:{window}".encode()).hexdigest()
    update = {"$inc": {"count": 1}, "$setOnInsert": {
        "expires": datetime.now(timezone.utc) + timedelta(seconds=seconds * 2)}}
    try:
        collection = MongoHandle.collection("rate_limits")
        try:
            doc = await collection.find_one_and_update(
                {"_id": key}, update, upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            doc = await collection.find_one_and_update(
                {"_id": key}, update, return_document=ReturnDocument.AFTER)
    except (PyMongoError, RuntimeError):
        raise HTTPException(503, "Rate limit service unavailable")
    if not doc:
        raise HTTPException(503, "Rate limit service unavailable")
    if doc["count"] > maximum:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(seconds)})


async def limit_user(user, action, maximum, seconds):
    await limit_key(str(user["_id"]), action, maximum, seconds)
