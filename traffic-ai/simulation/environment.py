import math
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import networkx as nx
    import osmnx as ox
except Exception:  # pragma: no cover - runtime dependency guard
    nx = None
    ox = None

from ml.predictor import CongestionPredictor


Coord = List[float]


class TrafficEnvironment:
    """Single intelligent vehicle routing on a real OSM road graph.

    AI reasoning:
    1. Build a real drivable road graph from OpenStreetMap.
    2. Snap source/destination to nearest road nodes.
    3. Run A* with dynamic edge cost modifiers.
    4. Re-run A* when traffic, accidents, or weather change.
    """

    def __init__(self) -> None:
        self.map_center = {'lat': 18.5204, 'lng': 73.8567}
        self.last_update_ts = time.time()

        self.graph_ready = False
        self.graph_error = ''

        self.osm_graph = None
        self.routing_graph = None

        self.is_running = False
        self.weather = 'Clear'
        self.weather_multiplier = 1.0
        self.global_traffic_bias = 1.0

        self.source_node = ''
        self.destination_node = ''
        self.source_coord: Coord = [self.map_center['lng'], self.map_center['lat']]
        self.destination_coord: Coord = [self.map_center['lng'], self.map_center['lat']]
        self.source_label = ''
        self.destination_label = ''
        self.has_custom_points = False

        self.current_route_nodes: List[str] = []
        self.current_route_coords: List[Coord] = []
        self.alternate_route_coords: List[Coord] = []
        self.initial_route_coords: List[Coord] = []

        self.vehicle_position: Coord = [self.map_center['lng'], self.map_center['lat']]
        self.vehicle_segment_index = 0
        self.vehicle_segment_progress = 0.0
        self.vehicle_speed = 0.0006
        self.manual_speed_kph = 36.0
        self.effective_speed_kph = 0.0

        self.traffic_zones: Dict[str, Dict[str, Any]] = {}
        self.accidents: Dict[str, Dict[str, Any]] = {}

        self.logs: List[str] = []
        self.ai_decision = 'Enter source and destination places, then click Start Navigation.'
        self.last_plan_strategy = 'IDLE'
        self.predictor = CongestionPredictor()
        self.ml_prediction: Dict[str, Any] = {
            'enabled': False,
            'label': 'Unavailable',
            'confidence': None,
            'training_accuracy': self.predictor.training_accuracy,
            'message': self.predictor.error_message or 'ML model not loaded.',
        }
        self.reroute_count = 0
        self.hurdles = {'traffic': 0, 'accident': 0, 'weather': 0}

        self.session_started_at: Optional[float] = None
        self.session_estimated_sec = 0.0
        self.session_actual_sec: Optional[float] = None
        self.session_completed = False

        self._build_osm_graph()

    @staticmethod
    def _edge_id(u: Any, v: Any) -> str:
        return f'{u}->{v}'

    @staticmethod
    def _coord_distance(a: Coord, b: Coord) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _build_osm_graph(self) -> None:
        if nx is None or ox is None:
            self.graph_error = 'Install osmnx and networkx for real OSM routing.'
            self.ai_decision = self.graph_error
            self.logs.append(self.graph_error)
            return

        try:
            center = (self.map_center['lat'], self.map_center['lng'])
            self.osm_graph = ox.graph_from_point(center, dist=5500, network_type='drive', simplify=True)
        except Exception as exc:
            self.graph_error = f'Failed to load OSM graph: {exc}'
            self.ai_decision = self.graph_error
            self.logs.append(self.graph_error)
            return

        # Build a single-edge directed graph with dynamic edge attributes used by A*.
        rg = nx.DiGraph()

        for node_id, data in self.osm_graph.nodes(data=True):
            rg.add_node(node_id, x=float(data['x']), y=float(data['y']))

        for u, v, _k, data in self.osm_graph.edges(keys=True, data=True):
            length = float(data.get('length', 1.0))
            if length <= 0:
                continue

            geometry_coords = None
            geom = data.get('geometry')
            if geom is not None:
                try:
                    geometry_coords = [[float(x), float(y)] for x, y in geom.coords]
                except Exception:
                    geometry_coords = None

            existing = rg.get_edge_data(u, v)
            if existing and existing.get('length', float('inf')) <= length:
                # Keep the shortest representative edge between same directed nodes.
                continue

            rg.add_edge(
                u,
                v,
                length=length,
                traffic_multiplier=1.0,
                weather_multiplier=1.0,
                blocked=False,
                geometry_coords=geometry_coords,
            )

        self.routing_graph = rg
        self.graph_ready = True

        self.logs.append('OSM road graph ready. Awaiting user route input.')

    def _nearest_node(self, lng: float, lat: float) -> Optional[Any]:
        if not self.graph_ready:
            return None
        try:
            return ox.distance.nearest_nodes(self.osm_graph, X=lng, Y=lat)
        except Exception:
            return None

    def _nearest_routing_edge(self, lng: float, lat: float) -> Optional[Tuple[Any, Any]]:
        if not self.graph_ready:
            return None

        try:
            u, v, _k = ox.distance.nearest_edges(self.osm_graph, X=lng, Y=lat)
        except Exception:
            return None

        if self.routing_graph.has_edge(u, v):
            return (u, v)
        if self.routing_graph.has_edge(v, u):
            return (v, u)
        return None

    def _heuristic(self, a: Any, b: Any) -> float:
        na = self.routing_graph.nodes[a]
        nb = self.routing_graph.nodes[b]
        # Euclidean heuristic in lon/lat plane (sufficient for local city scope).
        return math.hypot(float(nb['x']) - float(na['x']), float(nb['y']) - float(na['y']))

    def _edge_cost(self, data: Dict[str, Any]) -> float:
        if data.get('blocked', False):
            return float('inf')
        return (
            float(data.get('length', 1.0))
            * float(data.get('traffic_multiplier', 1.0))
            * float(data.get('weather_multiplier', 1.0))
            * self.weather_multiplier
            * self.global_traffic_bias
        )

    def _pathfind(self, start_node: Any, goal_node: Any) -> List[Any]:
        if not self.graph_ready:
            return []

        def weight(u: Any, v: Any, attrs: Dict[str, Any]) -> float:
            return self._edge_cost(attrs)

        try:
            return nx.astar_path(
                self.routing_graph,
                start_node,
                goal_node,
                heuristic=self._heuristic,
                weight=weight,
            )
        except Exception:
            return []

    def _path_length_m(self, node_path: List[Any]) -> float:
        if not node_path or len(node_path) < 2:
            return 0.0
        total = 0.0
        for i in range(len(node_path) - 1):
            total += float(self.routing_graph[node_path[i]][node_path[i + 1]].get('length', 0.0))
        return total

    def _estimate_eta_sec(self, length_m: float) -> float:
        speed_mps = max(1.0, self.manual_speed_kph / 3.6)
        return length_m / speed_mps

    @staticmethod
    def _time_of_day_from_hour(hour: int) -> str:
        if 5 <= hour <= 11:
            return 'Morning'
        if 12 <= hour <= 16:
            return 'Afternoon'
        if 17 <= hour <= 20:
            return 'Evening'
        return 'Night'

    def _route_distance_km(self) -> float:
        if not self.current_route_nodes or len(self.current_route_nodes) < 2:
            return 0.0
        total_m = 0.0
        for i in range(len(self.current_route_nodes) - 1):
            u = self.current_route_nodes[i]
            v = self.current_route_nodes[i + 1]
            try:
                total_m += float(self.routing_graph[int(u)][int(v)].get('length', 0.0))
            except Exception:
                continue
        return total_m / 1000.0

    def _route_span_km(self) -> float:
        dx = float(self.destination_coord[0]) - float(self.source_coord[0])
        dy = float(self.destination_coord[1]) - float(self.source_coord[1])
        # Local-scope longitude/latitude approximation is sufficient for relative route features.
        return max(0.35, math.hypot(dx, dy) * 111.0)

    def _route_heading(self) -> str:
        dx = float(self.destination_coord[0]) - float(self.source_coord[0])
        dy = float(self.destination_coord[1]) - float(self.source_coord[1])
        if abs(dx) < 1e-9 and abs(dy) < 1e-9:
            return 'Northbound'

        angle = (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0
        headings = [
            'Northbound',
            'NorthEast',
            'Eastbound',
            'SouthEast',
            'Southbound',
            'SouthWest',
            'Westbound',
            'NorthWest',
        ]
        return headings[int(((angle + 22.5) % 360.0) // 45.0)]

    def _route_turn_density(self) -> float:
        coords = self.current_route_coords
        if len(coords) < 3:
            return 0.2

        turns = 0
        for index in range(1, len(coords) - 1):
            ax = coords[index][0] - coords[index - 1][0]
            ay = coords[index][1] - coords[index - 1][1]
            bx = coords[index + 1][0] - coords[index][0]
            by = coords[index + 1][1] - coords[index][1]
            a_len = math.hypot(ax, ay)
            b_len = math.hypot(bx, by)
            if a_len < 1e-8 or b_len < 1e-8:
                continue

            dot = max(-1.0, min(1.0, (ax * bx + ay * by) / (a_len * b_len)))
            angle = math.degrees(math.acos(dot))
            if angle >= 22.0:
                turns += 1

        route_distance = max(self._route_distance_km(), 0.5)
        return round(min(9.5, max(0.2, turns / route_distance)), 2)

    def _coord_sector(self, coord: Coord) -> str:
        dx = float(coord[0]) - float(self.map_center['lng'])
        dy = float(coord[1]) - float(self.map_center['lat'])
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return 'Central'
        if dy >= 0 and dx >= 0:
            return 'NorthEast'
        if dy >= 0 and dx <= 0:
            return 'NorthWest'
        if dy <= 0 and dx >= 0:
            return 'SouthEast'
        return 'SouthWest'

    def _build_ml_features(self) -> Dict[str, Any]:
        local_time = time.localtime()
        hour = int(local_time.tm_hour)
        traffic_density = min(100, max(0, int(round((self.global_traffic_bias - 1.0) * 180.0))))
        num_vehicles = min(500, max(5, int(25 + traffic_density * 4.1 + len(self.traffic_zones) * 12)))
        signal_delay_sec = min(
            180,
            max(5, int(20 + traffic_density * 0.8 + len(self.accidents) * 18 + len(self.traffic_zones) * 9)),
        )
        route_distance_km = max(0.5, round(self._route_distance_km(), 2))
        travel_time_min = max(
            2.0,
            round(
                (
                    self.session_actual_sec
                    if self.session_actual_sec is not None
                    else self.session_estimated_sec
                )
                / 60.0,
                2,
            ),
        )
        avg_speed_kph = max(5.0, round(self.effective_speed_kph or self.manual_speed_kph, 2))
        route_span_km = round(self._route_span_km(), 2)
        route_directness = round(min(2.6, max(1.0, route_distance_km / max(route_span_km, 0.35))), 2)
        route_signal_pressure = round(min(35.0, max(0.5, signal_delay_sec / max(travel_time_min, 2.0))), 2)

        if route_distance_km < 4:
            route_context = 'InnerCore'
        elif route_directness > 1.45:
            route_context = 'DetourHeavy'
        elif traffic_density >= 70 or signal_delay_sec >= 100:
            route_context = 'CongestedCorridor'
        elif route_distance_km >= 18:
            route_context = 'CrossCity'
        else:
            route_context = 'Connector'

        return {
            'time_of_day': self._time_of_day_from_hour(hour),
            'hour': hour,
            'day_of_week': time.strftime('%A', local_time),
            'weather': self.weather,
            'traffic_density': traffic_density,
            'num_vehicles': num_vehicles,
            'avg_speed_kph': avg_speed_kph,
            'num_accidents': len(self.accidents),
            'road_block': 1 if self.accidents else 0,
            'signal_delay_sec': signal_delay_sec,
            'reroute_count': self.reroute_count,
            'route_distance_km': route_distance_km,
            'travel_time_min': travel_time_min,
            'source_sector': self._coord_sector(self.source_coord),
            'destination_sector': self._coord_sector(self.destination_coord),
            'route_heading': self._route_heading(),
            'route_span_km': route_span_km,
            'route_directness': route_directness,
            'route_turn_density': self._route_turn_density(),
            'route_signal_pressure': route_signal_pressure,
            'route_context': route_context,
        }

    def _update_ml_prediction(self) -> None:
        self.ml_prediction = self.predictor.predict(self._build_ml_features())

    def _build_upcoming_alert(self) -> Dict[str, Any]:
        if not self.is_running:
            return {'type': 'none', 'message': ''}

        nearest_alert: Optional[Dict[str, Any]] = None

        for zone in self.traffic_zones.values():
            distance = math.hypot(self.vehicle_position[0] - zone['lng'], self.vehicle_position[1] - zone['lat'])
            if distance <= 0.01:
                candidate = {
                    'type': 'traffic',
                    'distance': distance,
                    'message': 'Upcoming traffic ahead. Expect slower movement and possible rerouting.',
                }
                if nearest_alert is None or distance < nearest_alert['distance']:
                    nearest_alert = candidate

        for accident in self.accidents.values():
            distance = math.hypot(self.vehicle_position[0] - accident['lng'], self.vehicle_position[1] - accident['lat'])
            if distance <= 0.012:
                candidate = {
                    'type': 'accident',
                    'distance': distance,
                    'message': 'Upcoming accident zone detected. Vehicle is preparing to avoid the blocked road.',
                }
                if nearest_alert is None or distance < nearest_alert['distance']:
                    nearest_alert = candidate

        if nearest_alert is None:
            return {'type': 'none', 'message': ''}

        return {
            'type': nearest_alert['type'],
            'message': nearest_alert['message'],
        }

    def _compose_route_coords(self, node_path: List[Any], start_coord: Coord, end_coord: Coord) -> List[Coord]:
        if not node_path:
            return []

        coords: List[Coord] = [start_coord.copy()]

        for i in range(len(node_path) - 1):
            u, v = node_path[i], node_path[i + 1]
            edge_data = self.routing_graph[u][v]

            segment = edge_data.get('geometry_coords')
            if not segment:
                u_node = self.routing_graph.nodes[u]
                v_node = self.routing_graph.nodes[v]
                segment = [[float(u_node['x']), float(u_node['y'])], [float(v_node['x']), float(v_node['y'])]]

            for pt in segment:
                if self._coord_distance(coords[-1], pt) > 1e-8:
                    coords.append([pt[0], pt[1]])

        if self._coord_distance(coords[-1], end_coord) > 1e-8:
            coords.append(end_coord.copy())

        return coords

    def _replan_from_current_position(self) -> None:
        if not self.graph_ready:
            self.ai_decision = self.graph_error or 'Graph not ready.'
            return

        start_node = self._nearest_node(self.vehicle_position[0], self.vehicle_position[1])
        goal_node = self._nearest_node(self.destination_coord[0], self.destination_coord[1])
        if start_node is None or goal_node is None:
            self.ai_decision = 'Unable to snap to OSM road nodes.'
            self.last_plan_strategy = 'NO_PATH'
            return

        path = self._pathfind(start_node, goal_node)
        if not path:
            self.current_route_nodes = []
            self.current_route_coords = []
            self.ai_decision = 'No valid OSM path found. Roads may be blocked by incidents.'
            self.last_plan_strategy = 'NO_PATH'
            self.logs.append('Planner: A* failed after environment change.')
            return

        previous_nodes = self.current_route_nodes.copy()
        previous_coords = self.current_route_coords.copy()

        self.current_route_nodes = [str(n) for n in path]
        self.current_route_coords = self._compose_route_coords(
            path,
            [self.vehicle_position[0], self.vehicle_position[1]],
            self.destination_coord,
        )
        self.vehicle_segment_index = 0
        self.vehicle_segment_progress = 0.0
        self.alternate_route_coords = previous_coords

        if previous_nodes and previous_nodes != self.current_route_nodes:
            self.reroute_count += 1

        self.last_plan_strategy = 'DYNAMIC_A_STAR_OSM'
        self.ai_decision = f'OSM A* replanned route with {len(path)} road nodes.'
        self.logs.append(f'Planner: OSM replan successful ({len(path)} nodes).')

    def start(self) -> Dict[str, Any]:
        if not self.graph_ready:
            return {'status': 'error', 'message': self.graph_error or 'OSM graph unavailable'}

        self.is_running = True
        self.logs.append('Navigation started.')
        return {'status': 'ok', 'message': 'Navigation started'}

    def stop(self) -> Dict[str, Any]:
        self.is_running = False
        self.logs.append('Navigation paused.')
        return {'status': 'ok', 'message': 'Navigation paused'}

    def reset(self) -> Dict[str, Any]:
        if not self.graph_ready:
            return {'status': 'error', 'message': self.graph_error or 'OSM graph unavailable'}

        for _, _, data in self.routing_graph.edges(data=True):
            data['traffic_multiplier'] = 1.0
            data['blocked'] = False

        self.traffic_zones = {}
        self.accidents = {}
        self.weather = 'Clear'
        self.weather_multiplier = 1.0
        self.global_traffic_bias = 1.0

        self.vehicle_position = self.source_coord.copy()
        self.vehicle_segment_index = 0
        self.vehicle_segment_progress = 0.0

        self._replan_from_current_position()
        self.logs.append('Environment reset to baseline.')
        return {'status': 'ok', 'message': 'Environment reset'}

    def set_route(self, source: str, destination: str, auto_start: bool = True) -> Dict[str, Any]:
        # Legacy node-id mode is not meaningful with real OSM ids exposed to users.
        return {
            'status': 'error',
            'message': 'Use coordinate route mode with source/destination place points.',
        }

    def set_route_by_points(
        self,
        source_lng: float,
        source_lat: float,
        destination_lng: float,
        destination_lat: float,
        source_label: Optional[str] = None,
        destination_label: Optional[str] = None,
        mark_custom_points: bool = True,
        auto_start: bool = True,
    ) -> Dict[str, Any]:
        if not self.graph_ready:
            return {'status': 'error', 'message': self.graph_error or 'OSM graph unavailable'}

        start_node = self._nearest_node(source_lng, source_lat)
        goal_node = self._nearest_node(destination_lng, destination_lat)
        if start_node is None or goal_node is None:
            return {'status': 'error', 'message': 'Could not map source/destination to road graph'}

        path = self._pathfind(start_node, goal_node)
        if not path:
            self.current_route_nodes = []
            self.current_route_coords = []
            self.ai_decision = 'No valid path available for selected places.'
            self.last_plan_strategy = 'NO_PATH'
            self.logs.append('Planner: no path for selected source/destination points.')
            return {'status': 'error', 'message': 'No path found for selected points'}

        self.source_node = str(start_node)
        self.destination_node = str(goal_node)
        self.source_coord = [float(source_lng), float(source_lat)]
        self.destination_coord = [float(destination_lng), float(destination_lat)]
        self.source_label = source_label or f'{source_lat:.5f}, {source_lng:.5f}'
        self.destination_label = destination_label or f'{destination_lat:.5f}, {destination_lng:.5f}'
        self.has_custom_points = mark_custom_points

        self.vehicle_position = self.source_coord.copy()
        self.vehicle_segment_index = 0
        self.vehicle_segment_progress = 0.0

        self.current_route_nodes = [str(n) for n in path]
        self.current_route_coords = self._compose_route_coords(path, self.source_coord, self.destination_coord)
        self.alternate_route_coords = []
        self.initial_route_coords = [coord.copy() for coord in self.current_route_coords]
        self.reroute_count = 0
        self.hurdles = {'traffic': 0, 'accident': 0, 'weather': 0}
        self.session_started_at = time.time()
        self.session_completed = False
        self.session_actual_sec = None

        total_len_m = self._path_length_m(path)
        self.session_estimated_sec = self._estimate_eta_sec(total_len_m)

        self.ai_decision = f'OSM A* set route from {self.source_label} to {self.destination_label}.'
        self.last_plan_strategy = 'DYNAMIC_A_STAR_OSM'
        self.logs.append(
            f'Route set from points. Snap nodes: {self.source_node} -> {self.destination_node}.'
        )

        if auto_start:
            self.is_running = True

        return {
            'status': 'ok',
            'message': 'Route set from map coordinates',
            'route': self.current_route_nodes,
            'snap_source': self.source_node,
            'snap_destination': self.destination_node,
        }

    def _edge_midpoint(self, u: Any, v: Any) -> Coord:
        edge = self.routing_graph[u][v]
        segment = edge.get('geometry_coords')
        if segment and len(segment) > 0:
            idx = len(segment) // 2
            return [float(segment[idx][0]), float(segment[idx][1])]

        nu = self.routing_graph.nodes[u]
        nv = self.routing_graph.nodes[v]
        return [
            (float(nu['x']) + float(nv['x'])) / 2.0,
            (float(nu['y']) + float(nv['y'])) / 2.0,
        ]

    def add_traffic_zone(self, lng: float, lat: float, intensity: float = 0.45) -> Dict[str, Any]:
        if not self.graph_ready:
            return {'status': 'error', 'message': self.graph_error or 'OSM graph unavailable'}

        edge_uv = self._nearest_routing_edge(lng, lat)
        if not edge_uv:
            return {'status': 'error', 'message': 'No nearby road edge found'}

        u, v = edge_uv
        edge = self.routing_graph[u][v]
        edge['traffic_multiplier'] = min(4.0, float(edge['traffic_multiplier']) + max(0.1, intensity))
        if self.routing_graph.has_edge(v, u):
            rev = self.routing_graph[v][u]
            rev['traffic_multiplier'] = min(4.0, float(rev['traffic_multiplier']) + max(0.1, intensity))

        edge_id = self._edge_id(u, v)
        mid = self._edge_midpoint(u, v)
        self.traffic_zones[edge_id] = {
            'edge_id': edge_id,
            'lng': round(mid[0], 6),
            'lat': round(mid[1], 6),
            'multiplier': round(float(edge['traffic_multiplier']), 2),
        }

        self.logs.append(f'Traffic zone added on edge {edge_id} (x{edge["traffic_multiplier"]:.2f}).')
        self.hurdles['traffic'] += 1
        self._replan_from_current_position()
        return {'status': 'ok', 'message': f'Traffic added on edge {edge_id}', 'edge_id': edge_id}

    def add_accident(self, lng: Optional[float] = None, lat: Optional[float] = None) -> Dict[str, Any]:
        if not self.graph_ready:
            return {'status': 'error', 'message': self.graph_error or 'OSM graph unavailable'}

        edge_uv: Optional[Tuple[Any, Any]] = None
        if lng is None or lat is None:
            for u, v, data in self.routing_graph.edges(data=True):
                if not data.get('blocked', False):
                    edge_uv = (u, v)
                    break
        else:
            edge_uv = self._nearest_routing_edge(lng, lat)

        if not edge_uv:
            return {'status': 'error', 'message': 'No available edge for accident placement'}

        u, v = edge_uv
        self.routing_graph[u][v]['blocked'] = True
        if self.routing_graph.has_edge(v, u):
            self.routing_graph[v][u]['blocked'] = True

        edge_id = self._edge_id(u, v)
        mid = self._edge_midpoint(u, v)
        self.accidents[edge_id] = {
            'edge_id': edge_id,
            'lng': round(mid[0], 6),
            'lat': round(mid[1], 6),
        }

        self.logs.append(f'Accident blocked edge {edge_id}.')
        self.hurdles['accident'] += 1
        self._replan_from_current_position()
        return {'status': 'ok', 'message': f'Accident added on edge {edge_id}', 'edge_id': edge_id}

    def set_weather(self, weather: str) -> Dict[str, Any]:
        multipliers = {
            'Clear': 1.0,
            'Rain': 1.25,
            'Fog': 1.4,
            'Storm': 1.7,
        }

        self.weather = weather if weather in multipliers else 'Clear'
        self.weather_multiplier = multipliers[self.weather]

        self.logs.append(f'Weather changed to {self.weather} (x{self.weather_multiplier:.2f} cost).')
        self.hurdles['weather'] += 1
        self._replan_from_current_position()
        return {'status': 'ok', 'message': f'Weather set to {self.weather}'}

    def set_density(self, density: int) -> Dict[str, Any]:
        density = max(0, min(100, int(density)))
        self.global_traffic_bias = 1.0 + (density / 180.0)
        self.logs.append(f'Global traffic bias set to x{self.global_traffic_bias:.2f}.')
        self._replan_from_current_position()
        return {'status': 'ok', 'message': f'Traffic density bias updated to {density}'}

    def manual_signal_override(self, signal_id: int, state: str) -> Dict[str, Any]:
        return {'status': 'error', 'message': 'Signal override not used in single-vehicle routing mode'}

    def set_speed(self, speed_kph: float) -> Dict[str, Any]:
        self.manual_speed_kph = max(10.0, min(100.0, float(speed_kph)))
        self.logs.append(f'Manual vehicle speed set to {self.manual_speed_kph:.1f} km/h.')
        return {'status': 'ok', 'message': f'Vehicle speed set to {self.manual_speed_kph:.1f} km/h'}

    def _advance_vehicle(self, dt: float) -> None:
        if not self.current_route_coords or len(self.current_route_coords) < 2:
            return

        edge_uv = self._nearest_routing_edge(self.vehicle_position[0], self.vehicle_position[1])
        local_edge_multiplier = 1.0
        local_blocked_penalty = 1.0
        if edge_uv:
            u, v = edge_uv
            edge_data = self.routing_graph[u][v]
            local_edge_multiplier = float(edge_data.get('traffic_multiplier', 1.0))
            if edge_data.get('blocked', False):
                local_blocked_penalty = 1.4

        # Nearby traffic and accidents impose additional local slowdown.
        near_traffic_penalty = 1.0
        for zone in self.traffic_zones.values():
            d = math.hypot(self.vehicle_position[0] - zone['lng'], self.vehicle_position[1] - zone['lat'])
            if d < 0.004:
                near_traffic_penalty += (0.004 - d) * 45.0

        near_accident_penalty = 1.0
        for acc in self.accidents.values():
            d = math.hypot(self.vehicle_position[0] - acc['lng'], self.vehicle_position[1] - acc['lat'])
            if d < 0.003:
                near_accident_penalty += (0.003 - d) * 75.0

        base_coord_speed = self.manual_speed_kph / 60000.0
        effective_speed = base_coord_speed / (
            max(1.0, self.weather_multiplier)
            * max(1.0, local_edge_multiplier)
            * local_blocked_penalty
            * near_traffic_penalty
            * near_accident_penalty
        )
        effective_speed = max(0.00012, min(0.0015, effective_speed))
        self.vehicle_speed = effective_speed
        self.effective_speed_kph = max(5.0, min(self.manual_speed_kph, effective_speed * 60000.0))

        remaining_move = effective_speed * dt

        while remaining_move > 0 and self.vehicle_segment_index < len(self.current_route_coords) - 1:
            start = self.current_route_coords[self.vehicle_segment_index]
            end = self.current_route_coords[self.vehicle_segment_index + 1]

            seg_dx = end[0] - start[0]
            seg_dy = end[1] - start[1]
            seg_len = math.hypot(seg_dx, seg_dy)

            if seg_len < 1e-12:
                self.vehicle_segment_index += 1
                self.vehicle_segment_progress = 0.0
                continue

            seg_remaining = seg_len * (1.0 - self.vehicle_segment_progress)
            if remaining_move < seg_remaining:
                self.vehicle_segment_progress += remaining_move / seg_len
                remaining_move = 0.0
            else:
                remaining_move -= seg_remaining
                self.vehicle_segment_index += 1
                self.vehicle_segment_progress = 0.0

            base = self.current_route_coords[self.vehicle_segment_index]
            if self.vehicle_segment_index < len(self.current_route_coords) - 1:
                nxt = self.current_route_coords[self.vehicle_segment_index + 1]
                self.vehicle_position = [
                    base[0] + (nxt[0] - base[0]) * self.vehicle_segment_progress,
                    base[1] + (nxt[1] - base[1]) * self.vehicle_segment_progress,
                ]
            else:
                self.vehicle_position = [base[0], base[1]]

        if self.vehicle_segment_index >= len(self.current_route_coords) - 1:
            self.is_running = False
            if self.session_started_at is not None:
                self.session_actual_sec = max(0.0, time.time() - self.session_started_at)
                self.session_completed = True
            self.ai_decision = 'Destination reached. Navigation complete.'

    def update_environment(self) -> None:
        now = time.time()
        dt = now - self.last_update_ts
        if dt < 0.6:
            return

        self.last_update_ts = now
        if not self.is_running:
            return

        self._advance_vehicle(dt)
        self.logs = self.logs[-80:]

    def get_current_route(self) -> Dict[str, Any]:
        self.update_environment()
        self._update_ml_prediction()

        return {
            'status': 'ok' if self.graph_ready else 'error',
            'graph_ready': self.graph_ready,
            'graph_error': self.graph_error,
            'is_running': self.is_running,
            'source': self.source_node,
            'destination': self.destination_node,
            'source_coord': {'lng': round(self.source_coord[0], 6), 'lat': round(self.source_coord[1], 6)},
            'destination_coord': {'lng': round(self.destination_coord[0], 6), 'lat': round(self.destination_coord[1], 6)},
            'source_label': self.source_label,
            'destination_label': self.destination_label,
            'has_custom_points': self.has_custom_points,
            'weather': self.weather,
            'weather_multiplier': self.weather_multiplier,
            'strategy': self.last_plan_strategy,
            'ai_decision': self.ai_decision,
            'route_nodes': self.current_route_nodes,
            'route_coords': self.current_route_coords,
            'initial_route_coords': self.initial_route_coords,
            'vehicle': {
                'id': 1,
                'lng': round(self.vehicle_position[0], 6),
                'lat': round(self.vehicle_position[1], 6),
                'speed': round(self.vehicle_speed, 6),
                'configured_speed_kph': round(self.manual_speed_kph, 1),
                'effective_speed_kph': round(self.effective_speed_kph, 1),
            },
            'alternate_route_coords': self.alternate_route_coords,
            'reroute_count': self.reroute_count,
            'hurdles': self.hurdles,
            'trip_summary': {
                'completed': self.session_completed,
                'estimated_time_sec': round(self.session_estimated_sec, 1),
                'actual_time_sec': round(self.session_actual_sec, 1) if self.session_actual_sec is not None else None,
            },
            'ml_prediction': self.ml_prediction,
            'upcoming_alert': self._build_upcoming_alert(),
            'traffic_zones': list(self.traffic_zones.values()),
            'accidents': list(self.accidents.values()),
            'graph_nodes': [],
            'active_agents': 1,
            'logs': self.logs[-20:],
            'map_center': self.map_center,
        }

    def get_state(self) -> Dict[str, Any]:
        route_payload = self.get_current_route()
        return {
            'is_running': route_payload['is_running'],
            'weather': route_payload['weather'],
            'vehicles': [
                {
                    'id': route_payload['vehicle']['id'],
                    'lat': route_payload['vehicle']['lat'],
                    'lng': route_payload['vehicle']['lng'],
                    'speed': route_payload['vehicle']['speed'],
                }
            ],
            'signals': [],
            'congestion': min(100, int((self.global_traffic_bias - 1.0) * 150 + len(self.traffic_zones) * 8)),
            'risk_level': 'HIGH' if self.accidents else 'LOW',
            'ai_decision': self.ai_decision,
            'active_agents': 1,
            'logs': route_payload['logs'],
            'map_center': self.map_center,
            'route_coords': self.current_route_coords,
            'traffic_zones': route_payload['traffic_zones'],
            'accidents': route_payload['accidents'],
            'initial_route_coords': route_payload['initial_route_coords'],
            'upcoming_alert': route_payload['upcoming_alert'],
            'graph_nodes': [],
            'source': self.source_node,
            'destination': self.destination_node,
            'source_coord': route_payload['source_coord'],
            'destination_coord': route_payload['destination_coord'],
            'source_label': self.source_label,
            'destination_label': self.destination_label,
            'has_custom_points': self.has_custom_points,
            'strategy': self.last_plan_strategy,
            'graph_ready': self.graph_ready,
            'graph_error': self.graph_error,
            'ml_prediction': route_payload['ml_prediction'],
        }


environment = TrafficEnvironment()


def update_environment() -> Dict[str, Any]:
    environment.update_environment()
    return environment.get_state()
