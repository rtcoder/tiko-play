import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest


@pytest.fixture
def twitch_auth():
    class Auth:
        closed=False
        def state(self): return {'configured':False,'status':'disconnected','login':None,'error':None}
        async def close(self): self.closed=True
    return Auth()
