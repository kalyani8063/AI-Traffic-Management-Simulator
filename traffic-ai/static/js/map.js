let map;
let vehicleMarker = null;
let sourceMarker = null;
let destinationMarker = null;
let accidentMarkers = [];
let routeVisible = true;
let mlBannerVisible = false;
let simulationClockTimer = null;

const POLL_INTERVAL_MS = 2000;

const routeSelection = {
  source: null,
  destination: null,
  sourceName: '',
  destinationName: '',
};
const ROUTE_SELECTION_STORAGE_KEY = 'traffic_ai_route_selection';

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

function updateSimulationClock() {
  const clock = document.getElementById('simulationClockValue');
  if (!clock) return;
  clock.textContent = new Date().toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function initSimulationClock() {
  updateSimulationClock();
  if (simulationClockTimer) {
    window.clearInterval(simulationClockTimer);
  }
  simulationClockTimer = window.setInterval(updateSimulationClock, 1000);
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
    persistRouteSelection();
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
  persistRouteSelection();
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

function persistRouteSelection() {
  try {
    window.localStorage.setItem(ROUTE_SELECTION_STORAGE_KEY, JSON.stringify(routeSelection));
  } catch (_error) {
    // Ignore storage failures and keep the in-memory selection.
  }
}

function restoreRouteSelection() {
  try {
    const raw = window.localStorage.getItem(ROUTE_SELECTION_STORAGE_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (saved?.source?.lng !== undefined && saved?.source?.lat !== undefined) {
      placePoint('source', Number(saved.source.lng), Number(saved.source.lat), saved.sourceName || '');
    }
    if (saved?.destination?.lng !== undefined && saved?.destination?.lat !== undefined) {
      placePoint('destination', Number(saved.destination.lng), Number(saved.destination.lat), saved.destinationName || '');
    }
  } catch (_error) {
    // Ignore malformed storage and continue with a blank selection.
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

function upsertInitialRoute(routeCoords) {
  upsertLineSource('initial-route-line', 'initial-route-line-layer', routeCoords, '#60a5fa', 2, [2, 2]);
}

function upsertAlternateRoute(routeCoords) {
  upsertLineSource('alt-route-line', 'alt-route-line-layer', routeCoords, '#f59e0b', 3, [1, 2]);
}

function upsertTrafficZones(zones) {
  const features = (zones || []).map((zone) => ({
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [zone.lng, zone.lat],
    },
    properties: {
      intensity: zone.multiplier || 1.2,
    },
  }));

  const data = { type: 'FeatureCollection', features };
  const source = map.getSource('traffic-zones');

  if (source) {
    source.setData(data);
    return;
  }

  map.addSource('traffic-zones', { type: 'geojson', data });
  map.addLayer({
    id: 'traffic-zones-layer',
    type: 'circle',
    source: 'traffic-zones',
    paint: {
      'circle-radius': [
        'interpolate',
        ['linear'],
        ['get', 'intensity'],
        1,
        10,
        3,
        22,
      ],
      'circle-color': '#f59e0b',
      'circle-opacity': 0.35,
      'circle-stroke-width': 1,
      'circle-stroke-color': '#ffd18a',
    },
  });
}

function renderAccidents(accidents) {
  accidentMarkers.forEach((marker) => marker.remove());
  accidentMarkers = [];

  (accidents || []).forEach((accident) => {
    const marker = new mapboxgl.Marker(markerElement('accident-marker'))
      .setLngLat([accident.lng, accident.lat])
      .addTo(map);
    accidentMarkers.push(marker);
  });
}

function updateLiveAlert(state) {
  const alertCard = document.getElementById('liveAlertCard');
  const alertLabel = document.getElementById('liveAlertLabel');
  const alertText = document.getElementById('liveAlertText');
  const upcomingAlert = state.upcoming_alert || { type: 'none', message: '' };

  if (upcomingAlert.type === 'traffic') {
    alertCard.classList.remove('hidden');
    alertLabel.textContent = 'Traffic Alert';
    alertText.textContent = upcomingAlert.message;
    return;
  }

  if (upcomingAlert.type === 'accident') {
    alertCard.classList.remove('hidden');
    alertLabel.textContent = 'Accident Alert';
    alertText.textContent = upcomingAlert.message;
    return;
  }

  alertCard.classList.add('hidden');
  alertLabel.textContent = 'Live Alert';
  alertText.textContent = 'Monitoring route conditions.';
}

function updateMlBanner(state) {
  const banner = document.getElementById('mlForecastBanner');
  const predictionValue = document.getElementById('mlForecastValue');
  const predictionMeta = document.getElementById('mlMetaText');
  const prediction = state.ml_prediction || {};
  const hasRoute =
    (
      Boolean(state.has_custom_points) &&
      Boolean(state.source_label || state.source_coord) &&
      Boolean(state.destination_label || state.destination_coord)
    ) ||
    (
      Boolean(routeSelection.source) &&
      Boolean(routeSelection.destination)
    );

  if (!hasRoute) {
    banner.classList.add('hidden');
    banner.classList.remove('ml-banner-show');
    mlBannerVisible = false;
    predictionValue.textContent = 'Unavailable';
    predictionMeta.textContent = 'Set both source and destination to start ML forecasting.';
    return;
  }

  const predictionText = prediction.enabled
    ? `${prediction.label}${prediction.confidence ? ` (${prediction.confidence}% confidence)` : ''}`
    : 'Unavailable';

  predictionValue.textContent = predictionText;
  predictionMeta.textContent = prediction.enabled
    ? `Training accuracy: ${prediction.training_accuracy || '-'}%`
    : (prediction.message || 'ML forecast unavailable');

  banner.classList.remove('hidden');
  if (!mlBannerVisible) {
    banner.classList.remove('ml-banner-show');
    void banner.offsetWidth;
    banner.classList.add('ml-banner-show');
    mlBannerVisible = true;
  }
}

function updateVehicleTarget(vehicle, shouldShow) {
  if (!vehicle || !shouldShow) {
    if (vehicleMarker) {
      vehicleMarker.remove();
      vehicleMarker = null;
    }
    return;
  }

  const target = [vehicle.lng, vehicle.lat];

  if (!vehicleMarker) {
    vehicleMarker = new mapboxgl.Marker(markerElement('vehicle-marker')).setLngLat(target).addTo(map);
    return;
  }

  vehicleMarker.setLngLat(target);
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
  updateLiveAlert(state);
  updateMlBanner(state);
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
    upsertInitialRoute(state.initial_route_coords || []);
    upsertAlternateRoute(state.alternate_route_coords || []);
    upsertTrafficZones(state.traffic_zones || []);
    renderAccidents(state.accidents || []);
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
      updateMlBanner({ ml_prediction: {}, has_custom_points: false });
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
      updateMlBanner({ ml_prediction: {}, has_custom_points: false });
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
    if (map.getLayer('initial-route-line-layer')) {
      map.setLayoutProperty('initial-route-line-layer', 'visibility', routeVisible ? 'visible' : 'none');
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
    restoreRouteSelection();
    pollState();
    setInterval(pollState, POLL_INTERVAL_MS);
  });
}

bindEvents();
initSimulationClock();
initMap();
