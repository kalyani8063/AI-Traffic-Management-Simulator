# 🚦 AI Traffic Management Simulator

### Dynamic AI-Based Route Planning using Flask & OpenStreetMap

An interactive **AI-powered traffic navigation simulator** that demonstrates how intelligent routing systems adapt to changing environments such as traffic congestion, accidents, and weather conditions.

The application simulates a **single intelligent vehicle** navigating a real road network while dynamically recalculating optimal routes using AI search techniques.

Built as an academic Artificial Intelligence project, this system showcases real-world concepts such as **state-space search, intelligent agents, and adaptive planning** — all running locally without paid APIs.

---

## 🌍 Project Overview

This project implements a Flask-based web application that performs **real-time navigation on an OpenStreetMap (OSM) road graph**.

A user selects a source and destination, and an AI routing system computes the best path.
An administrator can introduce simulated environmental disruptions (traffic, accidents, weather), forcing the system to **replan routes dynamically**.

The goal is to demonstrate how AI decision-making adapts under changing environmental constraints.

---

## ✨ Core Features

* Real OpenStreetMap road-network loading
* A* shortest-path routing on directed graphs
* Source & destination search using geocoding
* Live vehicle movement visualization on Mapbox
* Dynamic route replanning
* Traffic zone simulation
* Accident-based road blocking
* Weather-based routing penalties
* Adjustable vehicle speed controls
* Alternate route visualization after reroutes
* Trip analytics (ETA, actual time, reroutes, hurdles)
* Admin control dashboard with live monitoring
* JSON API architecture for simulation control

---

## 🧠 AI Concepts Implemented

| Concept                     | Implementation                               |
| --------------------------- | -------------------------------------------- |
| Intelligent Agent           | Single vehicle acts as decision-making agent |
| Problem Formulation         | Source → Destination navigation task         |
| State Space Search          | Road network modeled as graph states         |
| A* Search Algorithm         | Optimal route computation                    |
| Heuristic Search            | Euclidean distance heuristic                 |
| Planning & Replanning       | Route recalculated after environment changes |
| Knowledge-Based Environment | Traffic, accident & weather modifiers        |
| Rational Decision Making    | Lowest-cost path selection                   |

> Routing decisions adapt continuously based on environmental conditions.

---

## 🏗️ System Architecture

```
User Interface (Mapbox UI)
        │
        ▼
Flask Backend API
        │
        ├── Simulation Engine
        ├── OSM Road Graph
        ├── A* Routing System
        └── Environment Modifiers
                │
                ▼
        Dynamic Route Updates
```

---

## 🚗 User Workflow

1. Search for **source** and **destination** locations.
2. System geocodes locations into coordinates.
3. Coordinates snap to nearest OSM road nodes.
4. A* algorithm computes optimal route.
5. Vehicle begins navigation.
6. Admin modifies environment (traffic/accident/weather).
7. Route cost updates.
8. AI automatically replans and updates path.

---

## 🛠️ Admin Dashboard Capabilities

The `/dashboard` page acts as a **Traffic Control Center**.

### Simulation Controls

* Start / Pause simulation
* Reset environment

### Environment Simulation

* Add traffic zones (increase road cost)
* Insert accidents (block roads)
* Change weather:

  * Clear
  * Rain
  * Fog
  * Storm

### Monitoring

* Live vehicle tracking
* Route preview
* Weather status
* Strategy indicators
* Backend event logs

---

## ⚙️ Routing Logic (Technical)

Routes are computed using:

```
A* Search on Directed Road Graph
```

Edge cost calculation:

```
cost =
edge_length
× traffic_multiplier
× weather_multiplier
× global_weather_factor
× global_density_bias
```

Rules:

* Accident edges → infinite cost (blocked)
* Traffic zones → increased multiplier
* Weather → global penalty factor
* Replanning triggers automatically on environment updates

---

## 🌦️ Environment Simulation

| Condition     | Effect                            |
| ------------- | --------------------------------- |
| Traffic Zone  | Increases edge traversal cost     |
| Accident      | Blocks road edge                  |
| Weather       | Applies global routing multiplier |
| Density Bias  | Adjusts global traffic weight     |
| Speed Control | Alters effective vehicle speed    |

---

## 🔌 API Endpoints

### Simulation State

* `GET /api/current_route` — main simulation data
* `GET /api/state` — compatibility state payload

### Control

* `POST /api/start` — start simulation
* `POST /api/stop` — pause simulation
* `POST /api/reset` — reset environment
* `POST /api/set_route` — define navigation route

### Environment

* `POST /api/add_traffic`
* `POST /api/add_accident`
* `POST /api/set_weather`
* `POST /api/change_density`

### Vehicle Control

* `POST /api/set_speed`

### Utilities

* `GET /api/geocode` — place search via Nominatim

---

## 📁 Project Structure

```
traffic-ai/
│
├── app.py                 # Flask application entry
├── config.py              # Configuration & tokens
│
├── routes/
│   ├── main_routes.py     # UI routes
│   └── api_routes.py      # API endpoints
│
├── simulation/
│   └── environment.py     # Core routing & simulation engine
│
├── ai/                    # Placeholder AI modules
│
├── templates/
│   ├── index.html         # User interface
│   └── dashboard.html     # Admin dashboard
│
├── static/
│   ├── css/
│   └── js/
│
└── requirements.txt
```

---

## 🚀 Installation & Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-username/AI-Traffic-Management-Simulator.git
cd traffic-ai
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate (Windows PowerShell):

```bash
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Add Mapbox Token (optional)

```bash
$env:MAPBOX_TOKEN="your_mapbox_token"
```

### 5. Run Application

```bash
python app.py
```

Open:

* User View → http://127.0.0.1:5000/
* Admin Dashboard → http://127.0.0.1:5000/dashboard

---

## ⚠️ Current Limitations

* Requires internet access for OSM graph and geocoding.
* Single-vehicle simulation only.
* No authentication for admin endpoints.
* Simulation state stored in memory only.
* No automated testing suite.
* Placeholder AI modules not yet integrated into routing engine.

---

## 🔮 Future Improvements

* Multi-vehicle traffic simulation
* Reinforcement learning signal control
* Persistent simulation storage
* Authentication & role management
* Real-time WebSocket updates
* Integration of additional AI planning modules

---

## 🎓 Academic Context

Developed as part of an Artificial Intelligence coursework project to demonstrate:

* Search strategies
* Intelligent agents
* Planning systems
* Dynamic decision-making in uncertain environments

---

## 📜 License

This project is intended for educational and research purposes.
