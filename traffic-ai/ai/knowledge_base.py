from typing import Dict, Any


class TrafficKnowledgeBase:
    """Knowledge-based reasoning using simple IF-THEN rules."""

    def infer(self, state: Dict[str, Any]) -> Dict[str, Any]:
        congestion = state.get('congestion', 0)
        weather = state.get('weather', 'Clear')
        accidents = state.get('accidents', 0)

        risk_level = 'LOW'
        reasons = []

        # Example required rule:
        # IF congestion high AND rain THEN risk high.
        if congestion >= 70 and weather == 'Rain':
            risk_level = 'HIGH'
            reasons.append('High congestion combined with rain increases braking distance risk.')

        if accidents > 0:
            risk_level = 'HIGH'
            reasons.append('Active accident zone detected.')

        if congestion >= 85 and weather in {'Fog', 'Rain'}:
            risk_level = 'CRITICAL'
            reasons.append('Severe congestion under low-visibility conditions.')

        if not reasons:
            reasons.append('Traffic conditions stable.')

        return {
            'risk_level': risk_level,
            'reasons': reasons,
        }
