let map;
let vehicleMarker = null;
let sourceMarker = null;
let destinationMarker = null;
let routeVisible = true;

const POLL_INTERVAL_MS = 1200;

const routeSelection = {
  source: null,
  destination: null,
  sourceName: '',
  destinationName: '',
};

const vehicleAnim = {
  current: null,
  target: null,
  startedAt: 0,
  durationMs: POLL_INTERVAL_MS,
};

function markerElement(className) {
  const el = document.createElement('div');
  el.className = className;
  return el;
}

function fmtSeconds(sec) {
  if (sec === null || sec === undefined) return '-';
  const total = Math.max(0, Math.round(sec));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}m ${s}s`;
}

function setStatus(isRunning, hasAccident) {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');

  if (!isRunning) {
    dot.className = 'status-dot status-stopped';
    text.textContent = 'Paused';
    return;
  }

  if (hasAccident) {
    dot.className = 'status-dot status-warning';
    text.textContent = 'Warning';
    return;
  }

  dot.className = 'status-dot status-running';
  text.textContent = 'Running';
}

function placePoint(mode, lng, lat, label = '') {
  const coord = { lng, lat };

  if (mode === 'source') {
    routeSelection.source = coord;
    if (label) {
      routeSelection.sourceName = label;
      document.getElementById('sourceQuery').value = label;
    }

    if (!sourceMarker) {
      sourceMarker = new mapboxgl.Marker(markerElement('source-marker')).setLngLat([lng, lat]).addTo(map);
    } else {
      sourceMarker.setLngLat([lng, lat]);
    }
    return;
  }

  routeSelection.destination = coord;
  if (label) {
    routeSelection.destinationName = label;
    document.getElementById('destinationQuery').value = label;
  }

  if (!destinationMarker) {
    destinationMarker = new mapboxgl.Marker(markerElement('destination-marker')).setLngLat([lng, lat]).addTo(map);
  } else {
    destinationMarker.setLngLat([lng, lat]);
  }
}

function syncPointsFromState(state) {
  if (!state.has_custom_points) {
    return;
  }

  if (state.source_coord) {
    placePoint('source', state.source_coord.lng, state.source_coord.lat, state.source_label || '');
  }
  if (state.destination_coord) {
    placePoint('destination', state.destination_coord.lng, state.destination_coord.lat, state.destination_label || '');
  }
}

function upsertLineSource(sourceId, layerId, coords, color, width, dashArray = null) {
  const data = {
    type: 'Feature',
    geometry: { type: 'LineString', coordinates: coords || [] },
  };

  const source = map.getSource(sourceId);
  if (source) {
    source.setData(data);
    return;
  }

  map.addSource(sourceId, { type: 'geojson', data });
  const paint = {
    'line-color': color,
    'line-width': width,
    'line-opacity': 0.88,
  };
  if (dashArray) {
    paint['line-dasharray'] = dashArray;
  }

  map.addLayer({
    id: layerId,
    type: 'line',
    source: sourceId,
    paint,
    layout: {
      visibility: 'visible',
      'line-cap': 'round',
      'line-join': 'round',
    },
  });
}

function upsertRouteSource(routeCoords) {
  upsertLineSource('route-line', 'route-line-layer', routeCoords, '#00d4aa', 5);
}

function upsertAlternateRoute(routeCoords) {
  upsertLineSource('alt-route-line', 'alt-route-line-layer', routeCoords, '#f59e0b', 3, [1, 2]);
}

function updateVehicleTarget(vehicle, shouldShow) {
  if (!vehicle || !shouldShow) {
    if (vehicleMarker) {
      vehicleMarker.remove();
      vehicleMarker = null;
    }
    vehicleAnim.current = null;
    vehicleAnim.target = null;
    return;
  }

  const target = [vehicle.lng, vehicle.lat];

  if (!vehicleMarker) {
    vehicleMarker = new mapboxgl.Marker(markerElement('vehicle-marker')).setLngLat(target).addTo(map);
    vehicleAnim.current = target;
    vehicleAnim.target = target;
    return;
  }

  vehicleAnim.current = vehicleMarker.getLngLat().toArray();
  vehicleAnim.target = target;
  vehicleAnim.startedAt = performance.now();
}

function animateVehicleMarker(now) {
  if (!vehicleMarker || !vehicleAnim.current || !vehicleAnim.target) {
    requestAnimationFrame(animateVehicleMarker);
    return;
  }

  const t = Math.max(0, Math.min(1, (now - vehicleAnim.startedAt) / vehicleAnim.durationMs));
  const eased = t * t * (3 - 2 * t);

  const lng = vehicleAnim.current[0] + (vehicleAnim.target[0] - vehicleAnim.current[0]) * eased;
  const lat = vehicleAnim.current[1] + (vehicleAnim.target[1] - vehicleAnim.current[1]) * eased;

  vehicleMarker.setLngLat([lng, lat]);

  requestAnimationFrame(animateVehicleMarker);
}

function updateInfoCards(state) {
  document.getElementById('weatherValue').textContent = state.weather;
  document.getElementById('strategyValue').textContent = state.strategy;
  document.getElementById('decisionFeed').textContent = state.ai_decision;
  document.getElementById('effectiveSpeedValue').textContent = `${Math.round(state.vehicle?.effective_speed_kph || 0)} km/h`;

  const routeNodes = state.route_nodes || [];
  if (routeNodes.length > 1) {
    document.getElementById('routeNodesText').textContent = `${routeNodes.length} nodes (${routeNodes[0]} -> ${routeNodes[routeNodes.length - 1]})`;
  } else if (routeNodes.length === 1) {
    document.getElementById('routeNodesText').textContent = `1 node (${routeNodes[0]})`;
  } else {
    document.getElementById('routeNodesText').textContent = '-';
  }

  const summary = state.trip_summary || {};
  document.getElementById('etaText').textContent = fmtSeconds(summary.estimated_time_sec);
  document.getElementById('actualTimeText').textContent = summary.completed ? fmtSeconds(summary.actual_time_sec) : '-';

  const hurdles = state.hurdles || { traffic: 0, accident: 0, weather: 0 };
  document.getElementById('hurdlesText').textContent =
    `Traffic ${hurdles.traffic || 0} | Accident ${hurdles.accident || 0} | Weather ${hurdles.weather || 0} | Reroutes ${state.reroute_count || 0}`;

  const configuredSpeed = Math.round(state.vehicle?.configured_speed_kph || 36);
  document.getElementById('userSpeedSlider').value = String(configuredSpeed);
  document.getElementById('userSpeedValue').textContent = String(configuredSpeed);

  setStatus(state.is_running, (state.accidents || []).length > 0);
}

async function fetchRouteState() {
  const response = await fetch('/api/current_route');
  return response.json();
}

async function postApi(url, payload = {}) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return response.json();
}

async function geocodePlace(query) {
  const response = await fetch(`/api/geocode?query=${encodeURIComponent(query)}`);
  const data = await response.json();
  if (!response.ok || data.status === 'error') {
    throw new Error(data.message || 'Place not found');
  }
  return data;
}

async function pollState() {
  try {
    const state = await fetchRouteState();
    if (state.graph_ready === false) {
      document.getElementById('decisionFeed').textContent = state.graph_error || 'OSM graph not ready.';
      return;
    }

    updateInfoCards(state);
    syncPointsFromState(state);

    upsertRouteSource(state.has_custom_points ? (state.route_coords || []) : []);
    upsertAlternateRoute(state.alternate_route_coords || []);
    updateVehicleTarget(state.vehicle, state.is_running);
  } catch (error) {
    console.error('Polling failed:', error);
  }
}

function bindEvents() {
  document.getElementById('searchSourceBtn').addEventListener('click', async () => {
    const query = document.getElementById('sourceQuery').value.trim();
    if (!query) return;

    try {
      const place = await geocodePlace(query);
      routeSelection.sourceName = place.name;
      placePoint('source', place.lng, place.lat, place.name);
      map.flyTo({ center: [place.lng, place.lat], zoom: 13.2 });
    } catch (error) {
      document.getElementById('decisionFeed').textContent = `Source search failed: ${error.message}`;
    }
  });

  document.getElementById('searchDestinationBtn').addEventListener('click', async () => {
    const query = document.getElementById('destinationQuery').value.trim();
    if (!query) return;

    try {
      const place = await geocodePlace(query);
      routeSelection.destinationName = place.name;
      placePoint('destination', place.lng, place.lat, place.name);
      map.flyTo({ center: [place.lng, place.lat], zoom: 13.2 });
    } catch (error) {
      document.getElementById('decisionFeed').textContent = `Destination search failed: ${error.message}`;
    }
  });

  const speedSlider = document.getElementById('userSpeedSlider');
  speedSlider.addEventListener('input', () => {
    document.getElementById('userSpeedValue').textContent = speedSlider.value;
  });

  document.getElementById('applyUserSpeedBtn').addEventListener('click', async () => {
    await postApi('/api/set_speed', { speed_kph: Number(speedSlider.value) });
    await pollState();
  });

  const startBtn = document.getElementById('startNavigationBtn');
  startBtn.addEventListener('click', async () => {
    if (!routeSelection.source || !routeSelection.destination) {
      document.getElementById('decisionFeed').textContent = 'Search and set both source and destination first.';
      return;
    }

    await postApi('/api/set_route', {
      source: routeSelection.source,
      destination: routeSelection.destination,
      source_name: routeSelection.sourceName,
      destination_name: routeSelection.destinationName,
    });
    await postApi('/api/start');
    await pollState();
  });

  document.getElementById('routeLayerToggle').addEventListener('click', () => {
    routeVisible = !routeVisible;
    if (map.getLayer('route-line-layer')) {
      map.setLayoutProperty('route-line-layer', 'visibility', routeVisible ? 'visible' : 'none');
    }
    if (map.getLayer('alt-route-line-layer')) {
      map.setLayoutProperty('alt-route-line-layer', 'visibility', routeVisible ? 'visible' : 'none');
    }
  });
}

function initMap() {
  mapboxgl.accessToken = window.APP_CONFIG.mapboxToken;

  map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/dark-v11',
    center: [73.8567, 18.5204],
    zoom: 12.3,
  });

  map.on('load', () => {
    pollState();
    setInterval(pollState, POLL_INTERVAL_MS);
    requestAnimationFrame(animateVehicleMarker);
  });
}

bindEvents();
initMap();
