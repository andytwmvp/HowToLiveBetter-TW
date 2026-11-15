"""Shared read-only full-audit snapshot for tests of the current checkout."""
from functools import lru_cache

import retroactive_audit as audit


@lru_cache(maxsize=1)
def current_audit_report() -> dict:
    """Run the expensive full audit once for read-only assertions in this process.

    Tests that deliberately change audit inputs must clear this cache before
    checking the changed state. Callers must treat the returned report as
    read-only so independent contract assertions cannot affect each other.
    """
    return audit.audit()


def clear_current_audit_report() -> None:
    """Invalidate the shared report after an audit input changes."""
    current_audit_report.cache_clear()
