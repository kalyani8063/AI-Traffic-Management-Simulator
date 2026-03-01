from dataclasses import dataclass
from typing import Dict


VALID_STATES = ('RED', 'YELLOW', 'GREEN')


@dataclass
class TrafficSignal:
    signal_id: int
    lat: float
    lng: float
    state: str = 'RED'
    green_time: int = 20
    override: bool = False

    def set_state(self, new_state: str) -> None:
        if new_state in VALID_STATES:
            self.state = new_state

    def apply_constraint_satisfaction(self, peer_is_green: bool) -> None:
        """Simple CSP guard: avoid two conflicting adjacent GREEN signals."""
        if peer_is_green and self.state == 'GREEN':
            self.state = 'RED'

    def to_dict(self) -> Dict:
        return {
            'id': self.signal_id,
            'lat': round(self.lat, 6),
            'lng': round(self.lng, 6),
            'state': self.state,
            'green_time': self.green_time,
            'override': self.override,
        }
