import os
import secrets

from fastapi import APIRouter, Header, HTTPException, Response

from auth import GoogleAuthManager, GoogleAuthUnavailable

router = APIRouter()

manager = GoogleAuthManager()

# only the configured Calendar service may request tokens
def authorize_calendar(key: str | None):
	expected = os.getenv("GOOGLEAUTH_CALENDAR_SERVICE_KEY")

	if not expected:
		raise HTTPException(
			status_code=503,
			detail="Internal service authentication is not configured."
		)

	if not key or not secrets.compare_digest(key, expected):
		raise HTTPException(
			status_code=403,
			detail="Forbidden"
		)

@router.get("/status")
def status():
	return {
		"data": manager.get_status()
	}

@router.post("/internal/token")
def token(
	response: Response,
	x_googleauth_service_key: str | None = Header(default=None)
):
	# never cache OAuth credentials in HTTP caches
	response.headers["Cache-Control"] = "no-store"

	authorize_calendar(x_googleauth_service_key)

	try:
		credentials = manager.get_access_token()

	except GoogleAuthUnavailable:
		raise HTTPException(
			status_code=503,
			detail="Google authorization unavailable. Reconnect the account."
		)

	return {
		"data": credentials
	}