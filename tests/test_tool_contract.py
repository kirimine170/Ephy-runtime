from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from packages.tool_core import (
    ApprovalGrant,
    ApprovalPolicy,
    RequestOrigin,
    SourceTrust,
    ToolAuditEvent,
    ToolDefinition,
    ToolDecisionType,
    ToolInvocation,
    ToolPermission,
    ToolPolicyContext,
    ToolResultStatus,
    invocation_hash,
    plan_tool_invocation,
)


ROOT = "/workspace/project"


def _definition(
    *permissions: ToolPermission,
    approval_policy: ApprovalPolicy = ApprovalPolicy.NEVER,
) -> ToolDefinition:
    return ToolDefinition(
        name="files.read",
        version="1.0.0",
        description="Read a file inside the workspace",
        permissions=frozenset(permissions),
        approval_policy=approval_policy,
    )


def _invocation(source_trust: SourceTrust = SourceTrust.USER) -> ToolInvocation:
    return ToolInvocation(
        invocation_id="invoke_12345678",
        tool_name="files.read",
        tool_version="1.0.0",
        arguments={"path": "README.md"},
        workspace_root=ROOT,
        requested_by=RequestOrigin.MODEL,
        source_trust=source_trust,
    )


def _context(*permissions: ToolPermission, network_enabled: bool = False) -> ToolPolicyContext:
    return ToolPolicyContext(
        granted_permissions=frozenset(permissions),
        allowed_workspace_roots=(ROOT,),
        network_enabled=network_enabled,
    )


@pytest.mark.parametrize(
    "permission",
    [ToolPermission.WRITE_FILES, ToolPermission.EXECUTE_PROCESS, ToolPermission.NETWORK_ACCESS],
)
def test_sensitive_permissions_require_always_approval(permission: ToolPermission) -> None:
    with pytest.raises(ValidationError, match="approval_policy=always"):
        _definition(permission)


def test_read_only_invocation_is_allowed_with_granted_permission() -> None:
    decision = plan_tool_invocation(
        _definition(ToolPermission.READ_FILES),
        _invocation(),
        _context(ToolPermission.READ_FILES),
    )

    assert decision.decision == ToolDecisionType.ALLOW
    assert decision.reason_code == "policy_satisfied"


@pytest.mark.parametrize("source", [SourceTrust.LOCAL_UNTRUSTED, SourceTrust.EXTERNAL_UNTRUSTED])
def test_untrusted_context_cannot_request_tools(source: SourceTrust) -> None:
    decision = plan_tool_invocation(
        _definition(ToolPermission.READ_FILES),
        _invocation(source),
        _context(ToolPermission.READ_FILES),
    )

    assert decision.decision == ToolDecisionType.BLOCK
    assert decision.reason_code == "untrusted_source_cannot_request_tools"


def test_missing_permission_is_blocked() -> None:
    decision = plan_tool_invocation(
        _definition(ToolPermission.READ_FILES),
        _invocation(),
        _context(),
    )

    assert decision.decision == ToolDecisionType.BLOCK
    assert decision.reason_code == "permission_not_granted"


def test_sensitive_invocation_requires_exact_unexpired_approval() -> None:
    definition = ToolDefinition(
        name="files.read",
        version="1.0.0",
        description="Write a file inside the workspace",
        permissions=frozenset({ToolPermission.WRITE_FILES}),
        approval_policy=ApprovalPolicy.ALWAYS,
    )
    invocation = _invocation()
    context = _context(ToolPermission.WRITE_FILES)
    now = datetime(2026, 8, 4, tzinfo=timezone.utc)

    pending = plan_tool_invocation(definition, invocation, context, now=now)
    assert pending.decision == ToolDecisionType.CONFIRM
    assert pending.reason_code == "approval_required"

    approval = ApprovalGrant(
        invocation_hash=invocation_hash(invocation),
        expires_at=now + timedelta(minutes=5),
    )
    allowed = plan_tool_invocation(definition, invocation, context, approval, now=now)
    assert allowed.decision == ToolDecisionType.ALLOW


def test_changed_arguments_invalidate_approval() -> None:
    definition = ToolDefinition(
        name="files.read",
        version="1.0.0",
        description="Write a file inside the workspace",
        permissions=frozenset({ToolPermission.WRITE_FILES}),
        approval_policy=ApprovalPolicy.ALWAYS,
    )
    original = _invocation()
    approval = ApprovalGrant(
        invocation_hash=invocation_hash(original),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    changed = original.model_copy(update={"arguments": {"path": "pyproject.toml"}})

    decision = plan_tool_invocation(
        definition,
        changed,
        _context(ToolPermission.WRITE_FILES),
        approval,
    )

    assert decision.decision == ToolDecisionType.CONFIRM
    assert decision.reason_code == "approval_hash_mismatch"


def test_consumed_approval_cannot_be_reused() -> None:
    definition = ToolDefinition(
        name="files.read",
        version="1.0.0",
        description="Write a file inside the workspace",
        permissions=frozenset({ToolPermission.WRITE_FILES}),
        approval_policy=ApprovalPolicy.ALWAYS,
    )
    invocation = _invocation()
    now = datetime(2026, 8, 4, tzinfo=timezone.utc)
    approval = ApprovalGrant(
        invocation_hash=invocation_hash(invocation),
        expires_at=now + timedelta(minutes=5),
        consumed_at=now,
    )

    decision = plan_tool_invocation(
        definition,
        invocation,
        _context(ToolPermission.WRITE_FILES),
        approval,
        now=now,
    )

    assert decision.decision == ToolDecisionType.CONFIRM
    assert decision.reason_code == "approval_consumed"


def test_network_permission_is_blocked_when_egress_is_disabled() -> None:
    definition = ToolDefinition(
        name="files.read",
        version="1.0.0",
        description="Fetch a remote resource",
        permissions=frozenset({ToolPermission.NETWORK_ACCESS}),
        approval_policy=ApprovalPolicy.ALWAYS,
    )

    decision = plan_tool_invocation(
        definition,
        _invocation(),
        _context(ToolPermission.NETWORK_ACCESS),
    )

    assert decision.decision == ToolDecisionType.BLOCK
    assert decision.reason_code == "network_disabled"


def test_invocation_hash_is_stable_and_excludes_request_id() -> None:
    first = _invocation()
    second = first.model_copy(update={"invocation_id": "invoke_abcdefgh"})

    assert invocation_hash(first) == invocation_hash(second)


def test_audit_event_rejects_raw_arguments_and_content() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ToolAuditEvent.model_validate(
            {
                "timestamp": datetime.now(timezone.utc),
                "invocation_hash": "a" * 64,
                "tool_name": "files.read",
                "permissions": [ToolPermission.READ_FILES],
                "decision": ToolDecisionType.ALLOW,
                "result_status": ToolResultStatus.SUCCEEDED,
                "raw_arguments": {"path": "secret.txt"},
                "content": "secret",
            }
        )
