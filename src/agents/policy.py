def tool_permission(
    tool_name: str | None, allow_deadline_calculation: bool
) -> dict[str, str]:
    allowed = allow_deadline_calculation and tool_name == "calc_deadline"
    return {
        "permissionDecision": "allow" if allowed else "deny",
        "permissionDecisionReason": "허용된 도구만 실행합니다.",
    }
