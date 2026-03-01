from dataclasses import dataclass
from typing import Dict
import random


@dataclass
class Vehicle:
    vehicle_id: int
    lat: float
    lng: float
    speed: float

    def move(self, intensity: float = 1.0) -> None:
        """Move vehicle with a tiny randomized delta to simulate route progression."""
        # Calibrated small movement suitable for city-scale map rendering.
        delta_lat = random.uniform(-0.0007, 0.0007) * intensity
        delta_lng = random.uniform(-0.0009, 0.0009) * intensity
        self.lat += delta_lat
        self.lng += delta_lng

        self.speed = max(8.0, min(60.0, self.speed + random.uniform(-2.0, 2.5)))

    def to_dict(self) -> Dict:
        return {
            'id': self.vehicle_id,
            'lat': round(self.lat, 6),
            'lng': round(self.lng, 6),
            'speed': round(self.speed, 1),
        }
