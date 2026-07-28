"""Light unit tests for server routes and Pydantic models using pytest."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from server.app import app
from server.models.articles_model import DurationRequest, SourceModel
from server.models.user_model import RegisterModel, LoginModel, PreferencesModel, SendOTPRequest
from server.services.user_service import send_otp


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_user_models_validation():
    reg = RegisterModel(email="test@example.com", password="secretpassword")
    assert reg.email == "test@example.com"

    login = LoginModel(email="user@example.com", password="password123")
    assert login.email == "user@example.com"

    prefs = PreferencesModel(preferences=["Sports", "Technology"])
    assert "Sports" in prefs.preferences
    assert "Technology" in prefs.preferences


def test_duration_request_model():
    req = DurationRequest(durationMs=5000.0)
    assert req.durationMs == 5000.0


def test_source_model_validation():
    src = SourceModel(title="CNBC", url="https://www.cnbc.com")
    assert src.title == "CNBC"


@pytest.mark.asyncio
async def test_send_otp_failure_logging_output(capsys):
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)

    with patch("service.db.redis.RedisHandle.client", return_value=mock_redis):
        with patch("server.services.otp_service._send_smtp", side_effect=OSError("[Errno -3] Temporary failure in name resolution")):
            response = await send_otp(SendOTPRequest(email="user@example.com"))

            assert "session_token" in response
            assert response["message"] == "OTP generated (email delivery failed, check server logs)"

            captured = capsys.readouterr()
            out = captured.out

            assert "[ INFO ]" in out
            assert "[ FAIL ]" in out
            assert "[ WARN ]" in out
            assert "Email delivery failed" in out
