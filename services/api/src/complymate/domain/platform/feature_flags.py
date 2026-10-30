"""Feature flags: global default, overridden per tenant."""

from __future__ import annotations

DEFAULT_FLAGS: dict[str, bool] = {
    "ask_rules_chat": True,
    "program_builder_agent": True,
    "electronic_verification": False,
    "pep_provider": False,
    "xero_integration": False,
    "nz_jurisdiction": True,
    "smr_agent_helper": True,
}


def resolve(global_flags: dict[str, bool], tenant_flags: dict[str, bool]) -> dict[str, bool]:
    return {**DEFAULT_FLAGS, **global_flags, **tenant_flags}
