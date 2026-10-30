import uuid
from datetime import UTC, datetime, timedelta

import pytest

from complymate.domain.errors import Forbidden, FourEyesViolation, StepUpRequired
from complymate.domain.programs import approval
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import Principal, Scope, assert_four_eyes, authorize, check_record_access
from complymate.domain.rbac.roles import TENANT_ROLES


def principal(role: str, *, auth_age: int = 30, mfa: bool = True) -> Principal:
    return Principal(
        user_id=uuid.uuid4(),
        email=f"{role}@x",
        tenant_id=uuid.uuid4(),
        role_key=role,
        permissions=TENANT_ROLES[role].permissions,
        mfa_verified=mfa,
        auth_time=datetime.now(UTC) - timedelta(seconds=auth_age),
    )


def test_staff_has_own_scope_for_clients():
    assert authorize(principal("staff"), P.CLIENT_READ) is Scope.OWN


def test_auditor_cannot_update_clients():
    with pytest.raises(Forbidden):
        authorize(principal("auditor"), P.CLIENT_UPDATE)


def test_advisor_shared_scope():
    assert authorize(principal("advisor"), P.CLIENT_READ) is Scope.SHARED


def test_staff_can_only_draft_smr():
    p = principal("staff")
    authorize(p, P.SMR_CREATE_DRAFT)
    with pytest.raises(Forbidden):
        authorize(p, P.SMR_READ)


def test_step_up_required_for_sensitive_actions():
    with pytest.raises(StepUpRequired):
        authorize(principal("amlco", auth_age=3600), P.SMR_APPROVE, step_up_window_seconds=600)
    authorize(principal("amlco", auth_age=60), P.SMR_APPROVE, step_up_window_seconds=600)


def test_step_up_needs_mfa():
    with pytest.raises(StepUpRequired):
        authorize(principal("owner", mfa=False), P.USER_UPDATE)


def test_tenant_mismatch():
    p = principal("owner")
    with pytest.raises(Forbidden):
        authorize(p, P.CLIENT_READ, tenant_id=uuid.uuid4())


def test_record_access_own():
    p = principal("staff")
    check_record_access(Scope.OWN, p, owner_ids={p.user_id})
    with pytest.raises(Forbidden):
        check_record_access(Scope.OWN, p, owner_ids={uuid.uuid4()})


def test_four_eyes():
    a = uuid.uuid4()
    with pytest.raises(FourEyesViolation):
        assert_four_eyes(a, a)
    assert_four_eyes(a, uuid.uuid4())


def test_matrix_matches_design_highlights():
    assert P.BILLING_UPDATE in TENANT_ROLES["owner"].permissions
    assert P.BILLING_READ not in TENANT_ROLES["amlco"].permissions
    assert P.PROGRAM_APPROVE in TENANT_ROLES["senior_manager"].permissions
    assert P.PROGRAM_APPROVE not in TENANT_ROLES["amlco"].permissions
    assert P.DOCUMENT_READ_MASKED in TENANT_ROLES["auditor"].permissions
    assert P.DOCUMENT_READ not in TENANT_ROLES["auditor"].permissions


def test_program_approval_flow_and_four_eyes():
    author, reviewer, signer = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    st = approval.VersionState("draft", author, None, None, False)
    approval.submit_for_review(st, author)
    approval.amlco_review(st, reviewer, "amlco", True)
    with pytest.raises(FourEyesViolation):
        approval.sign_off(approval.VersionState(st.status, author, author, reviewer, False), author, "owner", True)
    approval.sign_off(st, signer, "senior_manager", True)
    assert st.status == "approved" and st.locked
