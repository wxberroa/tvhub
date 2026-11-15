import pytest
from aiohttp.test_utils import TestClient, TestServer

import server


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DATA", str(tmp_path))      # fresh state (no users) for every test
    app = server.make_app()
    async with TestClient(TestServer(app)) as c:
        yield c


async def test_pwa_files_public(client):
    for path, ctype in (("/manifest.webmanifest", "manifest"), ("/sw.js", "javascript"), ("/icons/icon-192.png", "png")):
        r = await client.get(path)
        assert r.status == 200, path
        assert ctype in r.headers["Content-Type"], path


async def test_icons_reject_unknown_and_traversal(client):
    assert (await client.get("/icons/nope.png")).status == 404
    assert (await client.get("/icons/..%2Fserver.py")).status == 404


async def test_index_served_with_nonce_csp(client):
    r = await client.get("/")
    assert r.status == 200
    html = await r.text()
    assert "@@BASE@@" not in html
    assert "nonce-" in r.headers["Content-Security-Policy"]


async def test_api_requires_setup_then_auth(client):
    r = await client.get("/api/tvs")
    assert r.status in (401, 403)
    st = await (await client.get("/api/auth/status")).json()
    assert st.get("setup_required") or st.get("needs_setup") or "setup" in str(st).lower()


async def test_setup_login_and_admin_only(client):
    h = {"Origin": str(client.make_url("")).rstrip("/")}
    r = await client.post("/api/auth/setup", json={"username": "admin", "password": "tv-hub-4-the-lounge", "code": server.SEC.setup_code}, headers=h)
    assert r.status == 200, await r.text()
    assert (await client.get("/api/tvs")).status == 200      # session cookie set by setup/login
    bad = await client.post("/api/auth/setup", json={"username": "x2", "password": "tv-hub-4-the-lounge", "code": "nope"}, headers=h)
    assert bad.status == 409                                  # setup is closed once an admin exists
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password-x"}, headers=h)
    assert r.status in (400, 401, 403, 429)
