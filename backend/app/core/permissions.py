"""
Server-side mirror of the frontend's ROLE_PERMISSIONS
(src/lib/types.ts). Keep these two in sync by hand -- the frontend
copy governs what UI renders, this copy is the actual access-control
boundary and is what every protected route depends on.
"""

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "photos:manage",
        "roles:manage",
        "comments:moderate",
        "requests:respond",
        "analytics:view",
    },
    "staff": {
        "photos:manage",
        "comments:moderate",
        "requests:respond",
        "analytics:view",
    },
    "customer": set(),
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())
