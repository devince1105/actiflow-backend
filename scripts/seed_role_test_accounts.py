"""Create or refresh local QA accounts for each externally supported role.

The script is idempotent. Credentials come from the untracked local .env file;
no plaintext password is stored in source control.
"""

import os
from datetime import datetime, timezone
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.organizer.organizer import Organizer
from app.models.user.user import User


ACCOUNT_ENV_KEYS = {
    "owner": "ROLE_TEST_OWNER_EMAIL",
    "admin": "ROLE_TEST_ADMIN_EMAIL",
    "member": "ROLE_TEST_MEMBER_EMAIL",
    None: "ROLE_TEST_USER_EMAIL",
}


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    password = required_env("ROLE_TEST_PASSWORD")
    organizer_uuid = UUID(required_env("ROLE_TEST_ORGANIZER_UUID"))

    db = SessionLocal()
    try:
        organizer = (
            db.query(Organizer)
            .filter(
                Organizer.uuid == organizer_uuid,
                Organizer.is_active == True,
                Organizer.is_deleted == False,
            )
            .first()
        )
        if not organizer:
            raise RuntimeError("ROLE_TEST_ORGANIZER_UUID is not an active organizer")

        for role, email_key in ACCOUNT_ENV_KEYS.items():
            email = required_env(email_key).lower()
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email)
                db.add(user)
                db.flush()

            user.password_hash = hash_password(password)
            user.is_active = True
            user.is_deleted = False
            user.is_email_verified = True
            user.email_verified_at = datetime.now(timezone.utc)

            membership = (
                db.query(OrganizerMembership)
                .filter(
                    OrganizerMembership.user_uuid == user.uuid,
                    OrganizerMembership.organizer_uuid == organizer_uuid,
                )
                .first()
            )

            if role is None:
                if membership:
                    membership.is_active = False
                    membership.is_deleted = True
                continue

            if not membership:
                membership = OrganizerMembership(
                    user_uuid=user.uuid,
                    organizer_uuid=organizer_uuid,
                )
                db.add(membership)

            membership.role = role
            membership.is_active = True
            membership.is_deleted = False
            membership.is_suspended = False
            membership.suspended_reason = None

        db.commit()
        print(f"QA role accounts are ready for organizer {organizer.name}.")
        for role, email_key in ACCOUNT_ENV_KEYS.items():
            print(f"- {role or 'website_user'}: {required_env(email_key)}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
