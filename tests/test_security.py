"""Security regressions using mocked DB, AI and external identity providers."""
import asyncio
import json
import sys
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.testclient import TestClient
from server.app import app
from server.auth import get_current_user
from server.models.articles_model import ChatMessage, DurationRequest
from server.models.user_model import RegisterModel, PreferencesModel, GoogleLoginRequest
from server.security import create_access_token, decode_session, verify_password, get_password_hash
from service.db.mongo import MongoHandle


@pytest.fixture(autouse=True)
def security_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-" * 4)
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize("duration", [0, -1, float("inf"), float("nan"), 3_600_001])
def test_duration_bounds(duration):
    with pytest.raises(ValidationError):
        DurationRequest(durationMs=duration)


@pytest.mark.parametrize("message", ["", "   ", "a" * 4001])
def test_chat_bounds(message):
    with pytest.raises(ValidationError):
        ChatMessage(message=message)


def test_password_and_preferences_bounds():
    for password in ("short", "é" * 40):
        with pytest.raises(ValidationError):
            RegisterModel(email="user@example.com", password=password)
    for prefs in (["Sports", "Sports"], ["$where"], ["Unknown"]):
        with pytest.raises(ValidationError):
            PreferencesModel(preferences=prefs)
    hashed = get_password_hash("long-enough-password")
    assert verify_password("long-enough-password", hashed)
    assert not verify_password("incorrect", hashed)
    assert not verify_password("anything", None)


def test_short_session_claims_and_legacy_rejection():
    token = create_access_token({"email": "user@example.com", "version": 2})
    claims = decode_session(token)
    assert claims["version"] == 2
    assert claims["exp"] - claims["iat"] == 3600
    assert claims["csrf"]
    legacy = jwt.encode({"email": "user@example.com"}, "test-secret-" * 4, algorithm="HS256")
    with pytest.raises(jwt.InvalidTokenError):
        decode_session(legacy)


def test_anonymous_cannot_chat_track_or_use_legacy_bearer():
    client = TestClient(app)
    for path, body in (("/chat", {"message": "Hello"}),
                       ("/chat/article", {"message": "Hello"}),
                       ("/feeds/article/track_time", {"durationMs": 5000})):
        response = client.post(path, json=body, headers={"Authorization": "Bearer arbitrary"})
        assert response.status_code == 401
    assert client.get("/store_article").status_code == 404
    assert "/store_article" not in app.openapi()["paths"]


def test_session_csrf_origin_and_revocation():
    collection = MagicMock()
    user = {"_id": "user1", "email": "user@example.com", "session_version": 0}
    collection.find_one = AsyncMock(return_value=user)
    collection.update_one = AsyncMock()
    token = create_access_token({"email": user["email"]})
    csrf = decode_session(token)["csrf"]
    client = TestClient(app)
    client.cookies.set("SNAPsession", token)
    with patch.object(MongoHandle, "collection", return_value=collection):
        assert client.get("/session").status_code == 200
        assert client.post("/logout", headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf}).status_code == 403
        assert client.post("/logout", headers={"Origin": "http://localhost:3000"}).status_code == 403
        assert client.post("/logout", headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf}).status_code == 200
        collection.update_one.assert_awaited_once_with({"_id": "user1"}, {"$inc": {"session_version": 1}})
        user["session_version"] = 1
        client.cookies.set("SNAPsession", token)
        assert client.get("/session").status_code == 401


def test_login_cookie_not_json_token():
    client = TestClient(app)
    token = create_access_token({"email": "user@example.com"})
    with patch("server.routes.auth_routes.auth_limit", new=AsyncMock()), patch(
        "server.routes.auth_routes.login_user", new=AsyncMock(return_value={"access_token": token})):
        response = client.post("/login", json={"email": "user@example.com", "password": "password"})
    assert response.json() == {"authenticated": True}
    cookies = response.headers.get_list("set-cookie")
    assert any("SNAPsession=" in cookie and "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie for cookie in cookies)


def test_request_body_and_pagination_limits():
    client = TestClient(app)
    assert client.post("/login", content=b"x" * 16385).status_code == 413
    for path in ("/feeds/0/20", "/feeds/1/101", "/feeds/search?page=0", "/feeds/search?limit=101"):
        assert client.get(path).status_code == 422


@pytest.mark.asyncio
async def test_chunked_body_is_bounded():
    from server.middleware import BodyLimitMiddleware
    downstream = AsyncMock()
    receive = AsyncMock(side_effect=[{"type": "http.request", "body": b"x" * 8192, "more_body": True},
                                    {"type": "http.request", "body": b"x" * 8193, "more_body": False}])
    sent = []
    async def send(message):
        sent.append(message)
    await BodyLimitMiddleware(downstream)({"type": "http", "method": "POST", "headers": []}, receive, send)
    assert sent[0]["status"] == 413
    downstream.assert_not_awaited()


@pytest.mark.asyncio
async def test_google_email_only_and_wrong_audience_rejected():
    from server.services.user_service import google_login_user
    with pytest.raises(HTTPException) as exc:
        await google_login_user(GoogleLoginRequest(email="victim@example.com"))
    assert exc.value.status_code == 401
    response = MagicMock(status_code=200)
    response.json.return_value = {"aud": "other-client", "expires_in": "3600", "email": "victim@example.com", "email_verified": "true"}
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    with patch("httpx.AsyncClient", return_value=client), pytest.raises(HTTPException) as exc:
        await google_login_user(GoogleLoginRequest(id_token="bad", email="victim@example.com"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_google_validated_identity_ignores_supplied_email():
    from server.services.user_service import google_login_user
    response = MagicMock(status_code=200)
    response.json.return_value = {"aud": "test-client", "expires_in": "3600", "email": "verified@example.com", "email_verified": "true"}
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value={"email": "verified@example.com"})
    with patch("httpx.AsyncClient", return_value=client), patch.object(MongoHandle, "collection", return_value=collection):
        result = await google_login_user(GoogleLoginRequest(id_token="valid", email="victim@example.com"))
    assert decode_session(result["access_token"])["email"] == "verified@example.com"


@pytest.mark.asyncio
async def test_otp_is_consumed_atomically():
    from server.services.otp_service import verify_otp
    redis = MagicMock()
    redis.getdel = AsyncMock(side_effect=[json.dumps({"email": "user@example.com", "otp": "123456"}), None])
    with patch("service.db.redis.RedisHandle.client", return_value=redis):
        assert await verify_otp("user@example.com", "123456", "a" * 32)
        assert not await verify_otp("user@example.com", "123456", "a" * 32)
    assert redis.getdel.await_count == 2


@pytest.mark.asyncio
async def test_rate_limits_shared_and_fail_closed():
    from server.limits import limit_key
    collection = MagicMock()
    collection.find_one_and_update = AsyncMock(return_value={"count": 6})
    with patch.object(MongoHandle, "collection", return_value=collection), pytest.raises(HTTPException) as exc:
        await limit_key("identity", "login", 5, 60)
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "60"
    with patch.object(MongoHandle, "collection", side_effect=RuntimeError), pytest.raises(HTTPException) as exc:
        await limit_key("identity", "login", 5, 60)
    assert exc.value.status_code == 503


@pytest.mark.parametrize("url", ["http://example.com", "https://user:pass@example.com", "https://example.com:8000"])
def test_scraper_rejects_unsafe_urls(url):
    from pipeline.scrapers.safe_fetch import resolve_public
    with pytest.raises(ValueError):
        resolve_public(url)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fe80::1"])
def test_scraper_rejects_internal_dns(ip):
    from pipeline.scrapers.safe_fetch import resolve_public
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, (ip, 443))]), pytest.raises(ValueError):
        resolve_public("https://example.com")


def test_article_storage_rejects_traversal(tmp_path):
    from service.blob.filestore import FileArticleStore
    store = FileArticleStore(tmp_path)
    for value in ("../secrets", "/etc/passwd", "a/../../b", ".."):
        with pytest.raises(ValueError):
            store.load_article(value)


@pytest.mark.asyncio
async def test_cancelled_chat_retains_slot_until_worker_finishes(monkeypatch):
    from server.services import chat_service
    started = threading.Event()
    release = threading.Event()
    def worker(**kwargs):
        started.set()
        release.wait(5)
        return "reply"
    monkeypatch.setitem(sys.modules, "service.chatbot.wiring", SimpleNamespace(get_chatbot_response=worker))
    task = asyncio.create_task(chat_service.run_chat("hello", {"_id": "user"}, None))
    await asyncio.to_thread(started.wait, 2)
    try:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert "user" in chat_service._users
        with pytest.raises(HTTPException) as exc:
            await chat_service.run_chat("again", {"_id": "user"}, None)
        assert exc.value.status_code == 503
    finally:
        release.set()
        await asyncio.gather(*chat_service._jobs)
        await asyncio.sleep(0)
    assert "user" not in chat_service._users
