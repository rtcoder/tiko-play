import pytest
from src.api.session import SessionManager
from src.core.models import AppError


def test_expiry_replay_and_multiple_sessions():
    now = [0.0]
    s = SessionManager("one", "http://127.0.0.1:1234", lambda: now[0])
    t = s.issue_launch_token()
    now[0] = 59.9
    a = s.exchange(t)
    with pytest.raises(AppError):
        s.exchange(t)
    t = s.issue_launch_token()
    now[0] = 119.9
    with pytest.raises(AppError):
        s.exchange(t)
    b = s.exchange(s.issue_launch_token())
    assert s.authenticate(a.id) == a and s.authenticate(b.id) == b
    with pytest.raises(AppError):
        s.validate_origin("http://evil.test")
    with pytest.raises(AppError):
        s.validate_host("evil.test")
    with pytest.raises(AppError):
        s.validate_csrf(a, "bad")
    with pytest.raises(AppError):
        s.validate_origin(None)
