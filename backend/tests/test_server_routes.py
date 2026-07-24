"""Light unit tests for server routes and Pydantic models using pytest."""

from starlette.testclient import TestClient
from server.app import app
from server.models.articles_model import DurationRequest, SourceModel
from server.models.user_model import RegisterModel, LoginModel, PreferencesModel


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
