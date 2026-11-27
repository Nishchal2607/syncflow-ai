from app.agents.planner import valid_plan, deterministic_plan
from app.orchestration.state_machine import can_transition
import pytest

def test_valid_fallback():
    assert valid_plan(deterministic_plan('Research two companies'))

@pytest.mark.parametrize('deps', [[-1], [1], [99], ['0'], [True], [0,0], None])
def test_invalid_edges(deps):
    assert not valid_plan([{'name':'research','agent':'research'}, {'name':'report','agent':'reporter','depends_on_index':deps}])

def test_terminal_states():
    for state in ('FAILED','CANCELLED','COMPLETED'):
        assert not can_transition(state,'RUNNING')
