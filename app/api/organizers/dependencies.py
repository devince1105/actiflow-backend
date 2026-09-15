#   app/api/organizers/dependencies.py

"""Compatibility exports for organizer routes.

All authorization logic lives in app.core.dependencies so old and new routes
cannot drift into different role rules.
"""

from app.core.dependencies import (
    require_current_organizer_admin as require_organizer_admin,
    require_current_organizer_member as require_organizer_member,
    require_current_organizer_owner as require_organizer_owner,
    require_super_admin,
)

__all__ = [
    "require_organizer_admin",
    "require_organizer_member",
    "require_organizer_owner",
    "require_super_admin",
]
