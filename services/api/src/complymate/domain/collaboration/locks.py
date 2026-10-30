"""Record locking while editing a program section (re-exported for collaboration features)."""

from complymate.domain.programs.service import LOCK_TTL, assert_lock, new_lock

__all__ = ["LOCK_TTL", "assert_lock", "new_lock"]
