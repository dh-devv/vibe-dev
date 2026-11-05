from src.agents.policy import tool_permission


def test_only_deadline_calculation_is_permitted() -> None:
    assert tool_permission("calc_deadline", True)["permissionDecision"] == "allow"
    assert tool_permission("shell", True)["permissionDecision"] == "deny"
    assert tool_permission("calc_deadline", False)["permissionDecision"] == "deny"
    assert tool_permission(None, True)["permissionDecision"] == "deny"
