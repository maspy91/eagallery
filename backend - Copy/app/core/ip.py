from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """CF-Connecting-IP is set by Cloudflare's edge and can't be spoofed
    past it. Falls back to request.client.host only for local dev."""
    return request.headers.get("CF-Connecting-IP") or (request.client.host if request.client else None)