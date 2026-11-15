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


async def test_users_list_flags_home_assistant_accounts(client):
    h = {"Origin": str(client.make_url("")).rstrip("/")}
    r = await client.post("/api/auth/setup", json={"username": "admin", "password": "tv-hub-4-the-lounge",
                                                   "code": server.SEC.setup_code}, headers=h)
    assert r.status == 200
    await server.SEC.add_ha_user("maria")
    users = {u["username"]: u for u in (await (await client.get("/api/users")).json())["users"]}
    assert users["maria"]["ha"] is True and users["admin"]["ha"] is False


# ---- play a media URL on the TV (LG webOS) — what media_player.play_media / Music Assistant use

class FakeTV(server.Driver):
    type = "webos"
    caps = {"play_media": True}

    def __init__(self, cfg, fail=False):
        super().__init__(cfg)
        self.played, self.fail = [], fail

    async def play_url(self, url, page=False):
        if self.fail:
            raise RuntimeError("La TV no está conectada")
        self.played.append(url)


@pytest.fixture
async def play_client(client, monkeypatch):
    monkeypatch.setattr(server.player, "lan_ip", lambda toward: "10.0.0.2")
    h = {"Origin": str(client.make_url("")).rstrip("/")}
    r = await client.post("/api/auth/setup", json={"username": "admin", "password": "tv-hub-4-the-lounge",
                                                   "code": server.SEC.setup_code}, headers=h)
    assert r.status == 200
    server.hub.tvs["lg"] = FakeTV({"id": "lg", "name": "LG", "host": "10.0.0.5"})
    server.hub.tvs["off"] = FakeTV({"id": "off", "name": "Off", "host": "10.0.0.6"}, fail=True)
    server.hub.tvs["nope"] = server.Driver({"id": "nope", "name": "Nope", "host": "10.0.0.7"})
    me = await (await client.get("/api/auth/status")).json()
    yield client, {**h, "X-CSRF-Token": me["csrf"]}
    for k in ("lg", "off", "nope"):
        server.hub.tvs.pop(k, None)


async def test_play_url_ok(play_client):
    client, h = play_client
    r = await client.post("/api/tvs/lg/play", json={"url": "http://192.168.1.2:8123/local/song.mp3"}, headers=h)
    assert r.status == 200
    page = server.hub.tvs["lg"].played[0]
    assert page.startswith("http://10.0.0.2:") and "/player/" in page          # the TV opens TVHub's player page, not the raw file
    token = page.rsplit("/", 1)[1]
    assert server.PLAYERS.get(token)["url"] == "http://192.168.1.2:8123/local/song.mp3"


async def test_player_page_public_and_carries_metadata(play_client):
    client, h = play_client
    await client.post("/api/tvs/lg/play", json={"url": "http://192.168.1.2/a/My%20Song.mp3",
                      "extra": {"metadata": {"title": "Shivers", "artist": "Ed Sheeran", "image": "http://x/c.jpg"}}}, headers=h)
    token = server.hub.tvs["lg"].played[0].rsplit("/", 1)[1]
    client.session.cookie_jar.clear()                                          # the TV has no login
    r = await client.get(f"/player/{token}")
    assert r.status == 200
    html = await r.text()
    assert "Shivers" in html and "Ed Sheeran" in html and "nonce-" in r.headers["Content-Security-Policy"]
    assert (await client.get("/player/not-a-token")).status == 404


async def test_second_track_reuses_open_page_and_keys_reach_it(play_client):
    client, h = play_client
    await client.post("/api/tvs/lg/play", json={"url": "http://x/1.mp3"}, headers=h)
    token = server.hub.tvs["lg"].played[0].rsplit("/", 1)[1]
    ws = await client.ws_connect(f"/ws/player/{token}")
    await client.post("/api/tvs/lg/play", json={"url": "http://x/2.mp3", "extra": {"title": "Two"}}, headers=h)
    msg = await ws.receive_json()
    assert msg["cmd"] == "load" and msg["url"] == "http://x/2.mp3" and msg["meta"]["title"] == "Two"
    assert len(server.hub.tvs["lg"].played) == 1                                # the browser was not reopened
    await client.post("/api/tvs/lg/key", json={"key": "MEDIA_PAUSE"}, headers=h)
    assert (await ws.receive_json())["cmd"] == "pause"
    await ws.close()


async def test_nowplaying_updates_open_page(play_client):
    client, h = play_client
    await client.post("/api/tvs/lg/play", json={"url": "http://ma:8097/flow/s/media_player.lg/media_player.lg.flac"}, headers=h)
    token = server.hub.tvs["lg"].played[0].rsplit("/", 1)[1]
    assert "title" not in server.PLAYERS.get(token)["meta"]                      # Music Assistant's player id is not a title
    ws = await client.ws_connect(f"/ws/player/{token}")
    r = await client.post("/api/tvs/lg/nowplaying", json={"title": "Shivers", "artist": "Ed Sheeran", "duration": 207, "position": 12.5,
                                                          "image": "http://ha:8123/api/media_player_proxy/x?token=t"}, headers=h)
    assert (await r.json())["live"] is True
    msg = await ws.receive_json()
    assert msg["cmd"] == "meta" and msg["meta"]["title"] == "Shivers" and msg["meta"]["duration"] == 207 and msg["meta"]["position"] == 12.5
    await ws.close()
    r = await client.post("/api/tvs/off/nowplaying", json={"title": "x"}, headers=h)
    assert (await r.json())["live"] is False


def test_clean_meta_variants():
    m = server.player.clean_meta({"media_title": "T", "media_artist": "A", "media_image_url": "http://i/x.png"}, url="http://h/f.mp3")
    assert m == {"title": "T", "artist": "A", "image": "http://i/x.png"}
    assert server.player.clean_meta(None, {"image": "javascript:alert(1)"}, url="http://h/dir/My%20Song.flac") == {"title": "My Song"}


@pytest.mark.parametrize("bad", ["", "ftp://x/y.mp3", "javascript:alert(1)", "http://a b/c", "file:///etc/passwd", "http://x/\ny"])
async def test_play_url_rejects_bad_urls(play_client, bad):
    client, h = play_client
    r = await client.post("/api/tvs/lg/play", json={"url": bad}, headers=h)
    assert r.status == 400 and not server.hub.tvs["lg"].played


async def test_play_url_unsupported_and_offline(play_client):
    client, h = play_client
    assert (await client.post("/api/tvs/nope/play", json={"url": "http://x/y.mp3"}, headers=h)).status == 400
    r = await client.post("/api/tvs/off/play", json={"url": "http://x/y.mp3"}, headers=h)
    assert r.status == 400 and "conectada" in (await r.json())["error"]
    assert (await client.post("/api/tvs/ghost/play", json={"url": "http://x/y.mp3"}, headers=h)).status == 404
