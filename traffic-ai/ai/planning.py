from typing import Dict, Any


def generate_traffic_plan(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a simulated action plan from current traffic state.

    Real systems would use planning under constraints (e.g., PDDL, MILP, RL).
    For now this returns deterministic rule-driven plan objects for UI integration.
    """
    congestion = state.get('congestion', 0)
    weather = state.get('weather', 'Clear')
    accidents = state.get('accidents', 0)

    if congestion > 75 or accidents > 0:
        strategy = 'PRIORITIZE_MAIN_CORRIDOR'
        recommendation = 'Extend green cycle on main avenue and reroute secondary traffic.'
    elif weather in {'Rain', 'Fog'}:
        strategy = 'SAFETY_FIRST'
        recommendation = 'Reduce speed advisories and increase amber duration.'
    else:
        strategy = 'BALANCED_FLOW'
        recommendation = 'Maintain adaptive timing and monitor bottlenecks.'

    return {
        'strategy': strategy,
        'recommendation': recommendation,
    }
