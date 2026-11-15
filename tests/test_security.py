import security as S


def test_password_rules():
    assert S.check_password("short1") is not None
    assert S.check_password("password1234") is not None          # too common
    assert S.check_password("aaaaaaaaaaaa") is not None          # repetitive
    assert S.check_password("alice-correct-horse", "alice") is not None  # contains username
    assert S.check_password("tv-hub-4-the-lounge") is None
    assert S.check_password(123456789012) is not None


def test_username_rules():
    assert S.check_username("ab") is not None
    assert S.check_username("Has Space") is not None
    assert S.check_username("wxbo_01") is None
    assert S.norm_username("  WXBO ") == "wxbo"


def test_security_headers_csp():
    h = S.security_headers(secure=True, ws_host="tv.local", nonce="abc")
    csp = h["Content-Security-Policy"]
    assert "'nonce-abc'" in csp and "worker-src 'self'" in csp and "manifest-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp or "frame-ancestors" in csp
    framed = S.security_headers(secure=False, ws_host="x", nonce="n", framed=True)
    assert "frame-ancestors 'self'" in framed["Content-Security-Policy"]
    assert framed["X-Frame-Options"] == "SAMEORIGIN"
