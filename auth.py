import os
import tempfile
import threading

from datetime import timezone
from pathlib import Path

from dotenv import load_dotenv
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parent

load_dotenv(ROOT / ".env")

DATA_DIR = Path(
	os.getenv("GOOGLEAUTH_DATA_DIR", str(ROOT / "secrets"))
).resolve()

CLIENT_FILE = DATA_DIR / "credentials.json"
TOKEN_FILE = DATA_DIR / "token.json"

# calendar event reading, creation, updating, and deletion
SCOPES = [
	"https://www.googleapis.com/auth/calendar.events"
]

class GoogleAuthUnavailable(Exception):
	pass

class GoogleAuthManager:
	def __init__(self):
		self._lock = threading.Lock()

    # run the local Google OAuth consent flow
	def login(self):
		if not CLIENT_FILE.is_file():
			raise FileNotFoundError(
				"Missing Google OAuth client credentials. "
				f"Place credentials.json in {DATA_DIR}"
			)

		flow = InstalledAppFlow.from_client_secrets_file(
			str(CLIENT_FILE),
			SCOPES
		)

		credentials = flow.run_local_server(
			host="localhost",
			port=0,
			open_browser=True,
			access_type="offline",
			prompt="consent"
		)

		if not credentials.refresh_token:
			raise GoogleAuthUnavailable(
				"Google did not return a refresh token. "
				"Please authorize the account again."
			)

		with self._lock:
			self._save(credentials)

		print("Google authorization completed successfully.")

    # save credentials atomically, avoiding partial JSON files
	def _save(self, credentials: Credentials):
		DATA_DIR.mkdir(parents=True, exist_ok=True)

		temporary_path = None

		try:
			with tempfile.NamedTemporaryFile(
				mode="w",
				encoding="utf-8",
				dir=DATA_DIR,
				prefix=".token-",
				suffix=".tmp",
				delete=False
			) as temporary:
				temporary_path = Path(temporary.name)
				temporary.write(credentials.to_json())

			os.chmod(temporary_path, 0o600)
			os.replace(temporary_path, TOKEN_FILE)

		finally:
			if temporary_path is not None:
				temporary_path.unlink(missing_ok=True)

    # return a valid access token, refreshing it if necessary
	def get_access_token(self):
		with self._lock:
			if not TOKEN_FILE.is_file():
				raise GoogleAuthUnavailable(
					"No Google account connected."
				)

			try:
				credentials = Credentials.from_authorized_user_file(
					str(TOKEN_FILE),
					SCOPES
				)
			except (ValueError, OSError) as error:
				raise GoogleAuthUnavailable(
					"Stored Google credentials are invalid."
				) from error

			if not credentials.valid:
				if not credentials.refresh_token:
					raise GoogleAuthUnavailable(
						"Google reauthorization is required."
					)

				try:
					credentials.refresh(Request())
				except GoogleAuthError as error:
					raise GoogleAuthUnavailable(
						"Google token refresh failed. "
						"Reauthorization may be required."
					) from error

				self._save(credentials)

			if not credentials.token:
				raise GoogleAuthUnavailable(
					"Google did not provide an access token."
				)

			expires_at = None

			if credentials.expiry is not None:
				expiry = credentials.expiry

				if expiry.tzinfo is None:
					expiry = expiry.replace(tzinfo=timezone.utc)

				expires_at = expiry.astimezone(
					timezone.utc
				).isoformat()

			return {
				"access_token": credentials.token,
				"token_type": "Bearer",
				"expires_at": expires_at
			}

    # check the connection without exposing credentials
	def get_status(self):
		try:
			self.get_access_token()

			return {
				"connected": True,
				"needs_reauth": False,
				"scopes": SCOPES
			}

		except GoogleAuthUnavailable:
			return {
				"connected": False,
				"needs_reauth": True,
				"scopes": SCOPES
			}