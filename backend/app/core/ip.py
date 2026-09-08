# backend/app/core/ip.py

from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """This backend runs on Render with no Cloudflare (or other) reverse
    proxy in front of it (see DEPLOY.md: Render <-> Vercel, cross-site,
    no same-origin proxy) -- CF-Connecting-IP is never set by anything
    trustworthy here. Trusting it let any client set an arbitrary,
    attacker-chosen value, so every IP-keyed rate limit (login, register,
    comments, AI, chat) could be bypassed outright by sending a fresh
    fake value on each request, or weaponized to lock out a specific
    victim by replaying their real IP.

    Render sits directly in front of this service and appends the real
    client IP as the LAST entry of X-Forwarded-For -- but it never
    clears/strips a client-supplied X-Forwarded-For, only appends to it,
    so the FIRST entry is still attacker-controlled and must not be
    trusted. Falls back to request.client.host only when the header is
    absent entirely (local dev, no proxy in the path at all).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client else None