let map;
let selectedTool = 'traffic';
let vehicleMarker = null;
let accidentMarkers = [];

const logsPanel = document.getElementById('logsPanel');

function markerElement(className) {
  const el = document.createElement('div');
  el.className = className;
  return el;
}

function appendLog(message, isError = false) {
  const row = document.createElement('div');
  const stamp = new Date().toLocaleTimeString();
  row.textContent = `${isError ? '[ERR]' : '[OK ]'} ${stamp}  ${message}`;
  logsPanel.prepend(row);
}

function updateStatus(state) {
  const dot = document.getElementById('systemStatusDot');
  const text = document.getElementById('systemStatusText');

  if (!state.is_running) {
    dot.className = 'status-dot status-stopped';
    text.textContent = 'Stopped';
  } else if ((state.accidents || []).length > 0) {
    dot.className = 'status-dot status-warning';
    text.textContent = 'Warning';
  } else {
    dot.className = 'status-dot status-running';
    text.textContent = 'Running';
  }
}

function upsertRoute(state) {
  const data = {
    type: 'Feature',
    geometry: {
      type: 'LineString',
      coordinates: state.route_coords || [],
    },
  };

  const source = map.getSource('route-line');
  if (source) {
    source.setData(data);
  } else {
    map.addSource('route-line', { type: 'geojson', data });
    map.addLayer({
      id: 'route-line-layer',
      type: 'line',
      source: 'route-line',
      paint: {
        'line-color': '#00d4aa',
        'line-width': 5,
        'line-opacity': 0.9,
      },
      layout: {
        'line-cap': 'round',
        'line-join': 'round',
      },
    });
  }

  if (!vehicleMarker && state.vehicle) {
    vehicleMarker = new mapboxgl.Marker(markerElement('vehicle-marker'))
      .setLngLat([state.vehicle.lng, state.vehicle.lat])
      .addTo(map);
  } else if (vehicleMarker && state.vehicle) {
    vehicleMarker.setLngLat([state.vehicle.lng, state.vehicle.lat]);
  }
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
  accidentMarkers.forEach((m) => m.remove());
  accidentMarkers = [];

  (accidents || []).forEach((accident) => {
    const marker = new mapboxgl.Marker(markerElement('accident-marker'))
      .setLngLat([accident.lng, accident.lat])
      .addTo(map);
    accidentMarkers.push(marker);
  });
}

function updateMonitoring(state) {
  updateStatus(state);
  document.getElementById('activeAgentsValue').textContent = String(state.active_agents || 1);
  document.getElementById('planningStrategyValue').textContent = state.strategy || 'DYNAMIC_A_STAR';
  document.getElementById('currentRouteValue').textContent = (state.route_nodes || []).slice(0, 3).join(' -> ') + (state.route_nodes?.length > 3 ? ' ...' : '') || '-';
  document.getElementById('weatherStateValue').textContent = state.weather || 'Clear';

  logsPanel.innerHTML = '';
  (state.logs || []).slice().reverse().forEach((line) => {
    const row = document.createElement('div');
    row.textContent = line;
    logsPanel.appendChild(row);
  });
}

async function postApi(url, payload = {}) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (data.status === 'error') {
    throw new Error(data.message || 'request failed');
  }
  return data;
}

async function fetchRouteState() {
  const response = await fetch('/api/current_route');
  return response.json();
}

async function refreshState() {
  try {
    const state = await fetchRouteState();
    updateMonitoring(state);
    upsertRoute(state);
    upsertTrafficZones(state.traffic_zones || []);
    renderAccidents(state.accidents || []);
  } catch (error) {
    appendLog(`state refresh failed: ${error.message}`, true);
  }
}

function setTool(toolName) {
  selectedTool = toolName;
  document.getElementById('toolTrafficBtn').classList.toggle('btn-neutral', toolName !== 'traffic');
  document.getElementById('toolTrafficBtn').classList.toggle('btn-warning', toolName === 'traffic');
  document.getElementById('toolAccidentBtn').classList.toggle('btn-neutral', toolName !== 'accident');
  document.getElementById('toolAccidentBtn').classList.toggle('btn-danger', toolName === 'accident');
}

function bindControls() {
  document.getElementById('startBtn').addEventListener('click', async () => {
    try {
      const res = await postApi('/api/start');
      appendLog(res.message);
    } catch (error) {
      appendLog(error.message, true);
    }
  });

  document.getElementById('stopBtn').addEventListener('click', async () => {
    try {
      const res = await postApi('/api/stop');
      appendLog(res.message);
    } catch (error) {
      appendLog(error.message, true);
    }
  });

  document.getElementById('resetBtn').addEventListener('click', async () => {
    try {
      const res = await postApi('/api/reset');
      appendLog(res.message);
      await refreshState();
    } catch (error) {
      appendLog(error.message, true);
    }
  });

  document.getElementById('weatherBtn').addEventListener('click', async () => {
    const weather = document.getElementById('weatherSelect').value;
    try {
      const res = await postApi('/api/set_weather', { weather });
      appendLog(`${res.message} (route cost updated)`);
      await refreshState();
    } catch (error) {
      appendLog(error.message, true);
    }
  });

  document.getElementById('toolTrafficBtn').addEventListener('click', () => setTool('traffic'));
  document.getElementById('toolAccidentBtn').addEventListener('click', () => setTool('accident'));

  setTool('traffic');
}

function initMap() {
  mapboxgl.accessToken = window.APP_CONFIG.mapboxToken;

  map = new mapboxgl.Map({
    container: 'dashboardMap',
    style: 'mapbox://styles/mapbox/dark-v11',
    center: [73.8567, 18.5204],
    zoom: 12.3,
  });

  map.on('click', async (event) => {
    const lng = event.lngLat.lng;
    const lat = event.lngLat.lat;

    try {
      if (selectedTool === 'traffic') {
        const res = await postApi('/api/add_traffic', { lng, lat, intensity: 0.45 });
        appendLog(`${res.message} (vehicle will slow/reroute around heavier cost)`);
      } else {
        const res = await postApi('/api/add_accident', { lng, lat });
        appendLog(`${res.message} (edge blocked, route replanned)`);
      }
      await refreshState();
    } catch (error) {
      appendLog(error.message, true);
    }
  });

  map.on('load', () => {
    refreshState();
    setInterval(refreshState, 2000);
  });
}

bindControls();
initMap();
