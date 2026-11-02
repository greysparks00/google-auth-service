from fastapi.testclient import TestClient

from api import routes
from Junction.services.relay.main import app


client = TestClient(app)


class FakeManager:
	def get_status(self):
		return {
			"connected": True,
			"needs_reauth": False,
			"scopes": [
				"https://www.googleapis.com/auth/calendar.events"
			]
		}

	def get_access_token(self):
		return {
			"access_token": "mock-access-token",
			"token_type": "Bearer",
			"expires_at": "2026-10-26T03:00:00+00:00"
		}


def test_health():
	response = client.get("/health")

	assert response.status_code == 200
	assert response.json()["status"] == "healthy"


def test_status(monkeypatch):
	monkeypatch.setattr(routes, "manager", FakeManager())

	response = client.get("/status")

	assert response.status_code == 200
	assert response.json()["data"]["connected"] is True


def test_token_requires_authentication(monkeypatch):
	monkeypatch.setenv(
		"GOOGLEAUTH_CALENDAR_SERVICE_KEY",
		"test-internal-secret"
	)

	monkeypatch.setattr(routes, "manager", FakeManager())

	response = client.post("/internal/token")

	assert response.status_code == 403


def test_token_rejects_incorrect_secret(monkeypatch):
	monkeypatch.setenv(
		"GOOGLEAUTH_CALENDAR_SERVICE_KEY",
		"test-internal-secret"
	)

	monkeypatch.setattr(routes, "manager", FakeManager())

	response = client.post(
		"/internal/token",
		headers={
			"X-Googleauth-Service-Key": "wrong-secret"
		}
	)

	assert response.status_code == 403


def test_token_returns_access_token(monkeypatch):
	monkeypatch.setenv(
		"GOOGLEAUTH_CALENDAR_SERVICE_KEY",
		"test-internal-secret"
	)

	monkeypatch.setattr(routes, "manager", FakeManager())

	response = client.post(
		"/internal/token",
		headers={
			"X-Googleauth-Service-Key": "test-internal-secret"
		}
	)

	assert response.status_code == 200

	data = response.json()["data"]

	assert data["access_token"] == "mock-access-token"
	assert data["token_type"] == "Bearer"
	assert response.headers["cache-control"] == "no-store"


def test_token_fails_closed_without_configuration(monkeypatch):
	monkeypatch.delenv(
		"GOOGLEAUTH_CALENDAR_SERVICE_KEY",
		raising=False
	)

	response = client.post(
		"/internal/token",
		headers={
			"X-Googleauth-Service-Key": "anything"
		}
	)

	assert response.status_code == 503