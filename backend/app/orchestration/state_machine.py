"""
Backend-enforced session state machine.

States: IDLE, PLANNING, RUNNING, PAUSED, AWAITING_APPROVAL, COMPLETED, FAILED, CANCELLED

This module is the single source of truth for which transitions are legal.
The coordinator must call `transition()` before mutating a session's status;
if the transition is illegal, an InvalidTransition error is raised and the
caller must reject the request (e.g. HTTP 409).
"""

class InvalidTransition(Exception):
    def __init__(self, current: str, attempted: str):
        super().__init__(f"Cannot transition from {current} to {attempted}")
        self.current = current
        self.attempted = attempted


STATES = {
    "IDLE", "PLANNING", "RUNNING", "PAUSED",
    "AWAITING_APPROVAL", "COMPLETED", "FAILED", "CANCELLED",
}

# Map of current_state -> set of states it may legally move to.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "IDLE": {"PLANNING", "CANCELLED"},
    "PLANNING": {"RUNNING", "FAILED", "CANCELLED"},
    "RUNNING": {"PAUSED", "AWAITING_APPROVAL", "COMPLETED", "FAILED", "CANCELLED"},
    "PAUSED": {"RUNNING", "CANCELLED", "PAUSED"},  # redirect while paused keeps it PAUSED
    "AWAITING_APPROVAL": {"RUNNING", "PAUSED", "CANCELLED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),
    "CANCELLED": set(),
}

TERMINAL_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def can_transition(current: str, target: str) -> bool:
    if current not in ALLOWED_TRANSITIONS:
        return False
    return target in ALLOWED_TRANSITIONS[current]


def transition(current: str, target: str) -> str:
    """Validate and return the new state, or raise InvalidTransition."""
    if target not in STATES:
        raise InvalidTransition(current, target)
    if not can_transition(current, target):
        raise InvalidTransition(current, target)
    return target
