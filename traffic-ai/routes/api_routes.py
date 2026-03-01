import json
import urllib.parse
import urllib.request

from flask import Blueprint, jsonify, request

from simulation.environment import environment


api_bp = Blueprint('api', __name__)


@api_bp.get('/api/state')
def api_state():
    return jsonify(environment.get_state())


@api_bp.get('/api/current_route')
def api_current_route():
    return jsonify(environment.get_current_route())


@api_bp.post('/api/start')
def api_start():
    return jsonify(environment.start())


@api_bp.post('/api/stop')
def api_stop():
    return jsonify(environment.stop())


@api_bp.post('/api/reset')
def api_reset():
    return jsonify(environment.reset())


@api_bp.post('/api/set_route')
def api_set_route():
    payload = request.get_json(silent=True) or {}
    source = payload.get('source')
    destination = payload.get('destination')

    # Coordinate-mode route input:
    # { "source": {"lng":..,"lat":..}, "destination": {"lng":..,"lat":..} }
    if isinstance(source, dict) and isinstance(destination, dict):
        try:
            source_lng = float(source.get('lng'))
            source_lat = float(source.get('lat'))
            destination_lng = float(destination.get('lng'))
            destination_lat = float(destination.get('lat'))
            source_name = str(payload.get('source_name', '')).strip() or None
            destination_name = str(payload.get('destination_name', '')).strip() or None
        except (TypeError, ValueError):
            return jsonify({'status': 'error', 'message': 'Invalid coordinate payload'}), 400

        return jsonify(
            environment.set_route_by_points(
                source_lng,
                source_lat,
                destination_lng,
                destination_lat,
                source_label=source_name,
                destination_label=destination_name,
                auto_start=True,
            )
        )

    # Legacy node-id route input:
    # { "source": "A1", "destination": "C3" }
    source_node = str(source or '').strip()
    destination_node = str(destination or '').strip()
    return jsonify(environment.set_route(source_node, destination_node, auto_start=True))


@api_bp.post('/api/add_traffic')
def api_add_traffic():
    payload = request.get_json(silent=True) or {}

    try:
        lng = float(payload.get('lng'))
        lat = float(payload.get('lat'))
        intensity = float(payload.get('intensity', 0.45))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'lng/lat are required numeric values'}), 400

    return jsonify(environment.add_traffic_zone(lng, lat, intensity=intensity))


@api_bp.post('/api/add_accident')
def api_add_accident():
    payload = request.get_json(silent=True) or {}
    lng = payload.get('lng')
    lat = payload.get('lat')

    if lng is None or lat is None:
        return jsonify(environment.add_accident())

    try:
        return jsonify(environment.add_accident(float(lng), float(lat)))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'lng/lat must be numeric'}), 400


@api_bp.post('/api/set_weather')
def api_set_weather():
    payload = request.get_json(silent=True) or {}
    weather = str(payload.get('weather', 'Clear')).strip()
    return jsonify(environment.set_weather(weather))


# Legacy endpoint compatibility for previously wired frontend buttons.
@api_bp.post('/api/change_weather')
def api_change_weather():
    payload = request.get_json(silent=True) or {}
    weather = str(payload.get('weather', 'Clear')).strip()
    return jsonify(environment.set_weather(weather))


@api_bp.post('/api/spawn_accident')
def api_spawn_accident():
    return jsonify(environment.add_accident())


@api_bp.post('/api/change_density')
def api_change_density():
    payload = request.get_json(silent=True) or {}
    density = payload.get('density', 40)
    return jsonify(environment.set_density(int(density)))


@api_bp.post('/api/set_speed')
def api_set_speed():
    payload = request.get_json(silent=True) or {}
    speed_kph = payload.get('speed_kph', 36)
    try:
        speed_kph = float(speed_kph)
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'speed_kph must be numeric'}), 400
    return jsonify(environment.set_speed(speed_kph))


@api_bp.post('/api/signal_override')
def api_signal_override():
    payload = request.get_json(silent=True) or {}
    signal_id = int(payload.get('signal_id', 0))
    state = str(payload.get('state', 'RED')).upper()
    return jsonify(environment.manual_signal_override(signal_id, state))


@api_bp.get('/api/geocode')
def api_geocode():
    """Resolve place names to coordinates using free OpenStreetMap Nominatim."""
    query = str(request.args.get('query', '')).strip()
    if not query:
        return jsonify({'status': 'error', 'message': 'query is required'}), 400

    url = (
        'https://nominatim.openstreetmap.org/search?'
        + urllib.parse.urlencode(
            {
                'q': query,
                'format': 'jsonv2',
                'limit': 1,
                'addressdetails': 0,
            }
        )
    )

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'AI-Traffic-Management-Simulator/1.0 (local-development)',
            'Accept': 'application/json',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return jsonify({'status': 'error', 'message': 'Geocoding service unavailable'}), 503

    if not payload:
        return jsonify({'status': 'error', 'message': 'Place not found'}), 404

    item = payload[0]
    return jsonify(
        {
            'status': 'ok',
            'name': item.get('display_name', query),
            'lng': float(item['lon']),
            'lat': float(item['lat']),
        }
    )
