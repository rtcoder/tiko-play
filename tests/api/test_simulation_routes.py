import pytest

from tests.api import test_routes

api = test_routes.api
login = test_routes.login


def payload(store):
    return {
        "expected_revision": store.snapshot().revision,
        "messages": [{"offset_ms": 0, "user_id": "viewer", "comment": "missing"}],
    }


def test_simulation_auth_and_isolation(api):
    c, sessions, store, bus = api
    body = payload(store)
    assert (
        c.post(
            "/api/simulation", json=body, headers={"Origin": sessions.origin}
        ).status_code
        == 401
    )
    h = login(c, sessions)
    assert (
        c.post(
            "/api/simulation", json=body, headers={"Origin": sessions.origin}
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/api/simulation", json=body, headers={**h, "Origin": "http://evil"}
        ).status_code
        == 403
    )
    before = store.path.read_bytes(), bus.recent(), c.get("/api/state").json()
    r = c.post("/api/simulation", json=body, headers=h)
    assert r.status_code == 200
    assert r.json()["decisions"][0]["reason"] == "no_mapping"
    assert r.json()["config_revision"] == body["expected_revision"]
    assert (store.path.read_bytes(), bus.recent(), c.get("/api/state").json()) == before
    body["expected_revision"] += 1
    assert c.post("/api/simulation", json=body, headers=h).status_code == 409


@pytest.mark.parametrize(
    "patch",
    [
        {"messages": []},
        {"messages": [{"offset_ms": -1, "user_id": "x", "comment": "a"}]},
        {"platform": "unknown"},
        {"messages": [{"offset_ms": 0, "user_id": "x", "comment": "a"}] * 1001},
    ],
)
def test_simulation_bounds(api, patch):
    c, sessions, store, _ = api
    assert (
        c.post(
            "/api/simulation",
            json={**payload(store), **patch},
            headers=login(c, sessions),
        ).status_code
        == 422
    )


def test_simulation_payload_limit_and_invalid_json(api):
    c, sessions, store, _ = api
    h = login(c, sessions)
    assert (
        c.post(
            "/api/simulation", content=b"x" * (4 * 1024 * 1024 + 1), headers=h
        ).status_code
        == 413
    )
    assert c.post("/api/simulation", content=b"{", headers=h).status_code == 422
    assert (
        c.post(
            "/api/simulation",
            json={**payload(store), "profile_id": "missing"},
            headers=h,
        ).status_code
        == 404
    )
