# backend/app/models/__init__.py
# EDITED FILE — replaces: app/models/__init__.py (whole-file replacement)
# Assumes comments + conversations are already wired in from previous
# rounds -- this just adds Notification on top.

# Importing every model module here guarantees they're registered on
# Base.metadata as soon as `app.models` is imported -- relied on by
# alembic/env.py for autogenerate/upgrade, in addition to the dynamic
# discover_models() scan used at app startup.
from app.models.auth_token import AuthToken  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.models.conversation import Conversation, ConversationMessage  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.photo import Photo, PhotoLike  # noqa: F401
from app.models.user import User  # noqa: F401
