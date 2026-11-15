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


# ---- optional "sign in with Home Assistant" on the direct port (add-on only)

@pytest.fixture
async def ha_client(client, monkeypatch):
    import addon
    monkeypatch.setattr(server, "INGRESS", True)
    monkeypatch.setattr(addon, "options", lambda d: {"ha_login": True})
    accepted = {"maria": "ha-secret-pw"}

    async def fake_auth(user, pw):
        return accepted.get(user) == pw
    monkeypatch.setattr(addon, "ha_auth", fake_auth)
    h = {"Origin": str(client.make_url("")).rstrip("/")}
    r = await client.post("/api/auth/setup", json={"username": "admin", "password": "tv-hub-4-the-lounge",
                                                   "code": server.SEC.setup_code}, headers=h)
    assert r.status == 200
    await client.post("/api/auth/logout", headers=h)
    client.session.cookie_jar.clear()
    return client, h


async def test_ha_login_gives_user_role(ha_client):
    client, h = ha_client
    r = await client.post("/api/auth/login", json={"username": "maria", "password": "ha-secret-pw"}, headers=h)
    assert r.status == 200
    assert (await r.json())["user"]["role"] == "user"
    assert (await client.get("/api/tvs")).status == 200
    assert (await client.get("/api/users")).status == 403           # no admin rights


async def test_ha_login_wrong_password_and_no_local_password(ha_client, monkeypatch):
    client, h = ha_client
    import addon
    r = await client.post("/api/auth/login", json={"username": "maria", "password": "nope-nope-nope"}, headers=h)
    assert r.status == 401
    await client.post("/api/auth/login", json={"username": "maria", "password": "ha-secret-pw"}, headers=h)
    client.session.cookie_jar.clear()
    monkeypatch.setattr(addon, "ha_auth", lambda u, p: _never())                    # HA down: the stored account must not accept a password
    r = await client.post("/api/auth/login", json={"username": "maria", "password": "ha-secret-pw"}, headers=h)
    assert r.status == 401


async def _never():
    return False


async def test_ha_login_cannot_take_over_a_local_account(ha_client, monkeypatch):
    client, h = ha_client
    import addon

    async def yes(user, pw):
        return True                                                  # HA would accept anything for "admin"
    monkeypatch.setattr(addon, "ha_auth", yes)
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "whatever-123456"}, headers=h)
    assert r.status == 401


async def test_ha_login_off_by_default(client, monkeypatch):
    import addon
    monkeypatch.setattr(server, "INGRESS", True)
    monkeypatch.setattr(addon, "options", lambda d: {})
    called = []

    async def spy(u, p):
        called.append(u)
        return True
    monkeypatch.setattr(addon, "ha_auth", spy)
    h = {"Origin": str(client.make_url("")).rstrip("/")}
    r = await client.post("/api/auth/login", json={"username": "maria", "password": "ha-secret-pw"}, headers=h)
    assert r.status in (401, 403, 409) and not called


async def test_status_flags_for_addon_direct_port(client, monkeypatch):
    import addon
    monkeypatch.setattr(server, "INGRESS", True)
    monkeypatch.setattr(addon, "options", lambda d: {})
    st = await (await client.get("/api/auth/status")).json()
    assert st["setup_required"] is True and st["addon"] is True and st["ha_login"] is False
    monkeypatch.setattr(addon, "options", lambda d: {"ha_login": True})
    st = await (await client.get("/api/auth/status")).json()
    assert st["setup_required"] is False and st["ha_login"] is True      # the login form is shown instead of the setup one
