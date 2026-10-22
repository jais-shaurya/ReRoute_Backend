"""
One-time admin password reset utility.
Reads the new password from a secure prompt — nothing is logged or stored in plain text.
Run once, then delete this script.
"""
import getpass
import sys

# Ensure project root is on the path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.database.models import AppUser
from app.security.auth import hash_password

ADMIN_EMAIL = "admin@reroute.local"


def main() -> None:
    print(f"\nReRoute — Admin password reset for: {ADMIN_EMAIL}")
    print("=" * 52)

    password = getpass.getpass("New password: ")
    if len(password) < 12:
        print("ERROR: Password must be at least 12 characters.")
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("ERROR: Passwords do not match.")
        sys.exit(1)

    db = next(get_db())
    try:
        user = db.query(AppUser).filter_by(email=ADMIN_EMAIL).first()
        if user is None:
            print(f"ERROR: No user found with email {ADMIN_EMAIL!r}")
            sys.exit(1)

        user.password_hash = hash_password(password)
        db.commit()
        print(f"\nPassword updated successfully for {ADMIN_EMAIL}.")
        print("You can now sign in at http://127.0.0.1:5500")
        print("\nDelete this script after use:\n  del scripts\\reset_admin_password.py")
    finally:
        db.close()


if __name__ == "__main__":
    main()
