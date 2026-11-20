"""Access password login, for Frixos firmware that supports one.

The device stores only hash = PBKDF2-HMAC-SHA256(password, salt, iter), with a salt
derived from its MAC. To log in we fetch a one-time nonce and send
HMAC-SHA256(hash, nonce); the device answers with an fx_session cookie (30 days).
The integration stores the same hash, never the password.
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

import aiohttp

ENDPOINT_CHALLENGE = "/api/auth/challenge"
ENDPOINT_LOGIN = "/api/auth/login"
_TIMEOUT = aiohttp.ClientTimeout(total=10)


class InvalidAuth(Exception):
    """The device has an access password and the one we have is missing or wrong."""


class AuthLocked(Exception):
    """Too many failed logins; the device refuses logins for a while."""

    def __init__(self, seconds: int) -> None:
        super().__init__(f"too many failed logins, locked for {seconds} s")
        self.seconds = seconds


async def async_get_challenge(session: aiohttp.ClientSession, base_url: str) -> dict[str, Any]:
    """Return the device's challenge; {"auth": False} on firmware without passwords.

    Older firmware answers an unknown path with a 302 to its captive portal page,
    so redirects are not followed and anything but a JSON object means no password.
    """
    async with session.get(
        f"{base_url}{ENDPOINT_CHALLENGE}", timeout=_TIMEOUT, allow_redirects=False
    ) as response:
        if response.status != 200:
            return {"auth": False}
        try:
            data = await response.json(content_type=None)
        except ValueError:
            return {"auth": False}
    return data if isinstance(data, dict) else {"auth": False}


def hash_password(password: str, challenge: dict[str, Any]) -> str:
    """Hash the way the device's web UI does (CPU bound; run it in an executor)."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), str(challenge["salt"]).encode(), int(challenge["iter"])
    ).hex()


async def async_login(session: aiohttp.ClientSession, base_url: str, password_hash: str | None) -> bool:
    """Log in when the device asks for it; the session's cookie jar keeps the cookie.

    Returns False when the device has no password. Raises InvalidAuth or AuthLocked.
    """
    challenge = await async_get_challenge(session, base_url)
    if not challenge.get("auth"):
        return False
    if challenge.get("locked"):
        raise AuthLocked(int(challenge["locked"]))
    if not password_hash:
        raise InvalidAuth("the device has an access password")
    nonce = str(challenge["nonce"])
    proof = hmac.new(bytes.fromhex(password_hash), bytes.fromhex(nonce), hashlib.sha256).hexdigest()
    async with session.post(
        f"{base_url}{ENDPOINT_LOGIN}", json={"nonce": nonce, "proof": proof}, timeout=_TIMEOUT
    ) as response:
        data = await response.json(content_type=None)
        if response.status == 200:
            return True
    if response.status == 429 or (isinstance(data, dict) and data.get("locked")):
        raise AuthLocked(int(data.get("locked", 30)) if isinstance(data, dict) else 30)
    raise InvalidAuth("wrong access password")


def new_cookie_session_kwargs() -> dict[str, Any]:
    """Session options that keep the device's cookie (an IP host needs unsafe=True)."""
    return {"cookie_jar": aiohttp.CookieJar(unsafe=True)}
