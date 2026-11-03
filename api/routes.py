import os
import secrets

from fastapi import APIRouter, Header, HTTPException, Response

from auth import GoogleAuthManager, GoogleAuthUnavailable

router = APIRouter()

manager = GoogleAuthManager()

# only the configured Calendar service may request tokens
def authorize_calendar(authorization: str | None):
    expected = os.getenv("API_KEY")

    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Service authentication is not configured."
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    supplied = authorization.removeprefix("Bearer ")

    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=403, detail="Forbidden")

@router.get("/status")
def status():
	return {
		"data": manager.get_status()
	}

@router.post("/internal/token")
def token(
    response: Response,
    authorization: str | None = Header(default=None)
):
    response.headers["Cache-Control"] = "no-store"

    authorize_calendar(authorization)

    try:
        credentials = manager.get_access_token()
    except GoogleAuthUnavailable:
        raise HTTPException(
            status_code=503,
            detail="Google authorization unavailable."
        )

    return {"data": credentials}