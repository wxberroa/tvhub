"""A tiny web player for the TV's browser.

Some TVs (LG webOS from the UQ series on) cannot play a media URL in a viewer, only open it in their browser, where
audio shows as a bare player. Instead TVHub serves its own page (/player/<token>) that plays the audio and shows the
title, artist and cover Home Assistant sent along, and that Home Assistant can pause / resume / replace through a WebSocket.
"""
import json
import secrets
import socket
import time
from urllib.parse import unquote, urlsplit

TTL = 12 * 3600
MAX_SESSIONS = 20
TEXT_KEYS = {"title": ("title", "media_title", "name"), "artist": ("artist", "media_artist", "subtitle"),
             "album": ("album", "media_album_name", "album_name")}
IMAGE_KEYS = ("image", "image_url", "thumb", "thumbnail", "media_image_url", "entity_picture", "cover")


def _http(u):
    return isinstance(u, str) and 0 < len(u) <= 2048 and urlsplit(u).scheme in ("http", "https") and not any(c.isspace() for c in u)


def clean_meta(*sources, url=""):
    """Title / artist / album / image from whatever Home Assistant (or Music Assistant) sent; tolerant of nesting."""
    flat = {}
    for src in sources:
        stack = [src]
        while stack:
            d = stack.pop()
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(v, dict):
                        stack.append(v)
                    elif isinstance(v, (str, int, float)):
                        flat.setdefault(str(k).lower(), str(v))
    out = {}
    for field, names in TEXT_KEYS.items():
        for n in names:
            if flat.get(n, "").strip():
                out[field] = flat[n].strip()[:200]
                break
    for n in IMAGE_KEYS:
        if _http(flat.get(n, "")):
            out["image"] = flat[n]
            break
    for field in ("duration", "position"):                          # seconds, e.g. Music Assistant's media_duration / media_position
        for n in (field, "media_" + field):
            try:
                v = float(flat[n])
            except (KeyError, ValueError):
                continue
            if 0 <= v <= 3 * 86400:
                out[field] = round(v, 1)
                break
    if "title" not in out:                                          # last resort: the file name (not Music Assistant's player id)
        name = unquote(urlsplit(url).path.rsplit("/", 1)[-1]).rsplit(".", 1)[0]
        if name and not name.startswith("media_player."):
            out["title"] = name[:200]
    return out


def lan_ip(toward):
    """This machine's address on the network that reaches `toward` (a TV), i.e. one the TV can call back."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((toward, 9))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return ""


class Sessions:
    def __init__(self):
        self.by_token = {}
        self.by_tv = {}

    def _gc(self):
        t = time.time()
        for tok in [k for k, v in self.by_token.items() if t - v["created"] > TTL]:
            self.drop(tok)
        while len(self.by_token) > MAX_SESSIONS:
            self.drop(min(self.by_token, key=lambda k: self.by_token[k]["created"]))

    def drop(self, token):
        s = self.by_token.pop(token, None)
        if s and self.by_tv.get(s["tv"]) == token:
            self.by_tv.pop(s["tv"], None)

    def create(self, tv_id, url, meta):
        self._gc()
        old = self.by_tv.get(tv_id)
        if old:
            self.drop(old)
        token = secrets.token_urlsafe(16)
        self.by_token[token] = {"tv": tv_id, "url": url, "meta": meta, "created": time.time(), "clients": set(), "state": {}}
        self.by_tv[tv_id] = token
        return token

    def get(self, token):
        s = self.by_token.get(token)
        if s and time.time() - s["created"] > TTL:
            self.drop(token)
            return None
        return s

    def live(self, tv_id):
        """The session of this TV if its page is open right now (a client is connected), else None."""
        s = self.get(self.by_tv.get(tv_id, ""))
        return s if s and s["clients"] else None

    async def send(self, s, msg):
        dead = []
        for ws in list(s["clients"]):
            try:
                await ws.send_str(json.dumps(msg))
            except Exception:                                # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            s["clients"].discard(ws)
