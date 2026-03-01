# 🚦 AI Traffic Management Simulator

An **AI-powered smart traffic management simulator** built using **Flask** and modern web technologies.
The system models a city traffic environment where **intelligent agents** dynamically control traffic flow, predict congestion, optimize signal timing, and plan safer routes.

This project demonstrates the practical implementation of multiple **Artificial Intelligence concepts** through an interactive **Uber-inspired real-time web interface**.

---

## 🌟 Project Overview

Urban traffic congestion is a major problem in modern cities. Traditional traffic systems operate on fixed rules and lack adaptive intelligence.

This project simulates a **Smart City Traffic Control Center** where AI continuously:

* Observes traffic conditions
* Makes rational decisions
* Optimizes signal timings
* Plans vehicle routes
* Predicts congestion risks

The system acts as a **virtual AI traffic command center**.

---

## 🧠 AI Concepts Implemented (From Academic Syllabus)

The simulator applies core Artificial Intelligence concepts:

| AI Concept              | Implementation                              |
| ----------------------- | ------------------------------------------- |
| Intelligent Agents      | Vehicles & traffic signals behave as agents |
| State Space Search      | Traffic environment modeled as states       |
| Problem Formulation     | Route finding problem definition            |
| Breadth First Search    | Basic path exploration                      |
| Depth First Search      | Route exploration simulation                |
| A* Search Algorithm     | Smart route optimization                    |
| Hill Climbing           | Traffic signal timing optimization          |
| Constraint Satisfaction | Prevent conflicting signals                 |
| Knowledge-Based Agents  | Rule-based risk prediction                  |
| Planning                | Congestion reduction strategies             |

---

## 🏗️ System Architecture

```
Frontend (Uber-style UI)
        │
        ▼
Flask Backend API
        │
        ├── Simulation Engine
        ├── AI Decision Modules
        ├── Knowledge Base
        └── Environment Model
        │
        ▼
Live Traffic State Updates (JSON)
```

---

## 🎮 Features

### 🚗 Public Simulation View

* Live city traffic map
* Animated vehicle agents
* Fastest vs Safest route comparison
* Traffic congestion visualization
* AI decision insights panel
* Risk heatmap layer

### 🧠 Traffic Control Dashboard (Admin)

* Start / Stop simulation
* Modify traffic density
* Change weather conditions
* Spawn accidents
* Manual signal override
* View AI reasoning logs

### 🤖 AI Capabilities

* Intelligent decision-making agents
* Dynamic signal optimization
* Route planning using A*
* Knowledge-based reasoning rules
* Environment-aware planning

---

## 🛠️ Tech Stack

### Backend

* Python
* Flask
* REST API Architecture

### Frontend

* HTML5
* Tailwind CSS
* Vanilla JavaScript
* Mapbox GL JS

### AI Modules

* Search Algorithms (BFS, DFS, A*)
* Rule-Based Reasoning
* Planning Engine
* Agent-Based Simulation

---

## 📁 Project Structure

```
traffic-ai/
│
├── app.py
├── routes/
│   ├── main_routes.py
│   └── api_routes.py
│
├── ai/
│   ├── agents.py
│   ├── search_algorithms.py
│   ├── planning.py
│   └── knowledge_base.py
│
├── simulation/
│   ├── environment.py
│   ├── vehicle.py
│   └── signals.py
│
├── templates/
│   ├── index.html
│   └── dashboard.html
│
├── static/
│   ├── css/
│   └── js/
│
└── requirements.txt
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/ai-traffic-simulator.git
cd ai-traffic-simulator
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate:

**Windows**

```
venv\Scripts\activate
```

**Mac/Linux**

```
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Add Mapbox Token

Open:

```
static/js/map.js
```

Replace:

```javascript
MAPBOX_TOKEN = "YOUR_TOKEN_HERE";
```

---

### 5️⃣ Run Application

```bash
python app.py
```

Open browser:

```
http://127.0.0.1:5000/
```

Admin dashboard:

```
http://127.0.0.1:5000/dashboard
```

---

## 🔄 Application Workflow

1. Simulation environment initializes
2. Agents perceive traffic conditions
3. AI algorithms analyze state
4. Planning module selects actions
5. Signals/routes updated
6. Frontend receives live updates

---

## 📊 Example API Response

`GET /api/state`

```json
{
  "vehicles":[{"id":1,"lat":19.07,"lng":72.87,"speed":32}],
  "signals":[{"id":3,"state":"GREEN"}],
  "congestion":72,
  "ai_decision":"Extended green signal duration"
}
```

---

## 🎓 Academic Relevance

This project was developed as part of an **Artificial Intelligence course** to demonstrate real-world applications of:

* Search strategies
* Logical agents
* Planning systems
* Knowledge representation
* Intelligent decision-making

---

## 🚀 Future Improvements

* Reinforcement Learning traffic signals
* Real traffic dataset integration
* Multi-agent deep learning simulation
* WebSocket real-time updates
* Predictive accident analytics

---

## 👩‍💻 Author

Developed as an academic and portfolio project demonstrating applied Artificial Intelligence and full-stack system design.

---

## 📜 License

This project is for educational and research purposes.
