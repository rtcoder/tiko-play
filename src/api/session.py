import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlsplit
from src.core.models import AppError


@dataclass(frozen=True)
class Session:
    id: str
    csrf_token: str


class SessionManager:
    def __init__(self, instance_id, origin, clock=time.monotonic):
        self.origin = origin
        self.host = urlsplit(origin).netloc
        self.clock = clock
        self.cookie_name = "tikoplay_" + instance_id.replace("-", "")
        self.tokens = {}
        self.sessions = {}

    def issue_launch_token(self):
        now = self.clock()
        self.tokens = {k: v for k, v in self.tokens.items() if v > now}
        if len(self.tokens) >= 32:
            self.tokens.pop(next(iter(self.tokens)))
        token = secrets.token_urlsafe(32)
        self.tokens[token] = now + 60
        return token

    def exchange(self, token):
        expiry = self.tokens.pop(token, 0)
        if expiry <= self.clock():
            raise AppError(
                "invalid_token",
                "Link wygasł. Otwórz panel z ikony TikoPlay.",
                status=401,
            )
        if len(self.sessions) >= 128:
            raise AppError(
                "session_limit",
                "Zbyt wiele sesji. Uruchom ponownie TikoPlay.",
                status=429,
            )
        session = Session(secrets.token_urlsafe(32), secrets.token_urlsafe(32))
        self.sessions[session.id] = session
        return session

    def authenticate(self, cookie):
        if cookie not in self.sessions:
            raise AppError("unauthorized", "Otwórz panel z ikony TikoPlay.", status=401)
        return self.sessions[cookie]

    def validate_host(self, host):
        if host != self.host:
            raise AppError("invalid_host", "Niedozwolony adres", status=403)

    def validate_origin(self, origin):
        if origin != self.origin:
            raise AppError("invalid_origin", "Niedozwolone źródło", status=403)

    def validate_csrf(self, session, token):
        if not token or not secrets.compare_digest(session.csrf_token, token):
            raise AppError("invalid_csrf", "Nieprawidłowa sesja", status=403)
