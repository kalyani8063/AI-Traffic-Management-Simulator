from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class BaseAgent:
    """Base intelligent agent abstraction with perceive-act cycle."""

    agent_id: int

    def perceive(self, environment_state: Dict[str, Any]) -> Dict[str, Any]:
        return environment_state

    def act(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        return {'action': 'NO_OP'}


@dataclass
class VehicleAgent(BaseAgent):
    """Vehicle agent that adapts driving behavior based on environment risk."""

    speed: float = 30.0

    def act(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        risk_level = perception.get('risk_level', 'LOW')
        weather = perception.get('weather', 'Clear')

        # Placeholder policy: lower speed in risky conditions.
        if risk_level == 'HIGH' or weather in {'Rain', 'Fog'}:
            self.speed = max(12.0, self.speed - 2.0)
            return {'action': 'SLOW_DOWN', 'new_speed': self.speed}

        self.speed = min(55.0, self.speed + 1.0)
        return {'action': 'CRUISE', 'new_speed': self.speed}


@dataclass
class SignalAgent(BaseAgent):
    """Traffic signal agent that controls light state and timing."""

    state: str = 'RED'
    green_time: int = 20

    def act(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        congestion = perception.get('congestion', 0)

        # Placeholder hill-climbing style update: step timing up or down.
        if congestion > 70:
            self.green_time = min(60, self.green_time + 5)
            self.state = 'GREEN'
            return {'action': 'EXTEND_GREEN', 'green_time': self.green_time, 'state': self.state}

        self.green_time = max(10, self.green_time - 2)
        self.state = 'RED' if self.state == 'GREEN' else 'GREEN'
        return {'action': 'TOGGLE', 'green_time': self.green_time, 'state': self.state}
