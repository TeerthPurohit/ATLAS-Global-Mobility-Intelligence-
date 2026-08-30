"""Clean, developer-friendly Documentation specification router for ATLAS API.

Structured directly after the Hermes Agent Docs format:
- Simple, clear prose without excessive academic jargon
- Practical step-by-step installation and quickstart guides
- Copy-paste ready terminal commands and multi-language snippets
- Clean, focused API endpoint references
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter

router = APIRouter(prefix="/api/docs", tags=["docs"])

DOCS_SPEC: dict[str, Any] = {
    "title": "ATLAS Mobility Intelligence",
    "version": "2.4.0",
    "description": (
        "The urban mobility intelligence platform built on 1.4B+ New York City TLC records. "
        "Delivers sub-85ms trip predictions, arterial congestion calibration, and deterministic SQL spatial analytics."
    ),
    "base_url": "http://localhost:8000",
    "categories": [
        {
            "id": "getting-started",
            "title": "Getting Started",
            "description": "Install, configure, and make your first API request in minutes.",
            "sections": [
                {
                    "id": "quick-install",
                    "title": "Quick Install & Setup",
                    "content": (
                        "### Install and Run ATLAS Locally\n\n"
                        "ATLAS runs out-of-the-box with Python 3.10+ and Node.js 18+.\n\n"
                        "#### 1. Clone and Install Dependencies\n\n"
                        "```bash\n"
                        "git clone https://github.com/TeerthPurohit/Uber-nyc-TLC-Dataset.git\n"
                        "cd \"Uber nyc TLC Dataset\"\n"
                        "pip install -r requirements.txt\n"
                        "```\n\n"
                        "#### 2. Start the Backend API Server\n\n"
                        "```bash\n"
                        "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload\n"
                        "```\n\n"
                        "#### 3. Launch the Web Dashboard\n\n"
                        "```bash\n"
                        "cd frontend-web\n"
                        "npm install\n"
                        "npm run dev\n"
                        "```\n\n"
                        "The web interface will be live at `http://localhost:3000` and the API at `http://localhost:8000`."
                    ),
                },
                {
                    "id": "first-request",
                    "title": "Making Your First Request",
                    "content": (
                        "### Your First Journey Estimation\n\n"
                        "Send a quick POST request to calculate the optimal departure time and fare from Times Square to JFK Airport:\n\n"
                        "```bash\n"
                        "curl -X POST \"http://localhost:8000/api/mobility/departure-time\" \\\n"
                        "  -H \"Content-Type: application/json\" \\\n"
                        "  -d '{\n"
                        "    \"pickup_lat\": 40.7580,\n"
                        "    \"pickup_lon\": -73.9855,\n"
                        "    \"dropoff_lat\": 40.6413,\n"
                        "    \"dropoff_lon\": -73.7781,\n"
                        "    \"vehicle_type\": \"sedan\"\n"
                        "  }'\n"
                        "```\n\n"
                        "#### Example JSON Response\n\n"
                        "```json\n"
                        "{\n"
                        "  \"recommended_departure_time\": \"2026-08-31T08:15:00\",\n"
                        "  \"estimated_duration_minutes\": 48.0,\n"
                        "  \"distance_miles\": 18.4,\n"
                        "  \"fare_estimate\": {\n"
                        "    \"min_fare\": 58.50,\n"
                        "    \"max_fare\": 74.00,\n"
                        "    \"surge_multiplier\": 1.18,\n"
                        "    \"basis\": \"computed\"\n"
                        "  }\n"
                        "}\n"
                        "```"
                    ),
                },
            ],
        },
        {
            "id": "core-features",
            "title": "Core Features",
            "description": "Discover how the mobility engine, spatial context, and AI analyst work.",
            "sections": [
                {
                    "id": "journey-engine",
                    "title": "Smart Journey Engine",
                    "content": (
                        "### Predictive Route & Departure Intelligence\n\n"
                        "- **Optimal Departure Window**: Computes the exact time to leave to avoid peak tunnel and bridge bottlenecks.\n"
                        "- **Multi-Vehicle Fleet Pricing**: Compares standard Sedan, SUV, Green EV, Luxury, and Wheelchair-Accessible (WAV) fares.\n"
                        "- **Carbon Emission Tracking**: Estimates vehicle emissions in grams of CO₂ per passenger mile."
                    ),
                },
                {
                    "id": "spatial-context",
                    "title": "Real-Time Spatial Context",
                    "content": (
                        "### Environmental Intelligence Layer\n\n"
                        "- **Live Arterial Traffic**: Detects bridge/tunnel congestion and corridor slowdowns.\n"
                        "- **Weather Impact**: Integrates live precipitation and visibility multipliers.\n"
                        "- **Holiday Calendar**: Automatically applies holiday schedule modifications."
                    ),
                },
                {
                    "id": "ai-analyst",
                    "title": "AI Mobility Analyst",
                    "content": (
                        "### Natural Language to SQL Grounding\n\n"
                        "Ask natural questions like *\"What are the top 5 pickup zones by average fare?\"*.\n\n"
                        "ATLAS compiles your question into deterministic SQL AST queries executed against real DuckDB marts with **zero hallucinations**."
                    ),
                },
            ],
        },
        {
            "id": "api-reference",
            "title": "API Reference",
            "description": "Complete reference for all REST endpoints and WebSockets.",
            "endpoints": [
                {
                    "id": "post-departure-time",
                    "method": "POST",
                    "path": "/api/mobility/departure-time",
                    "summary": "Optimal Departure & Fare Estimate",
                    "description": "Calculates best departure time, traffic bottleneck multipliers, and calibrated fares.",
                    "parameters": [
                        {"name": "pickup_lat", "type": "float", "required": True, "description": "Origin latitude (e.g. 40.7580 for Midtown).", "example": 40.7580},
                        {"name": "pickup_lon", "type": "float", "required": True, "description": "Origin longitude (e.g. -73.9855).", "example": -73.9855},
                        {"name": "dropoff_lat", "type": "float", "required": True, "description": "Destination latitude.", "example": 40.6413},
                        {"name": "dropoff_lon", "type": "float", "required": True, "description": "Destination longitude.", "example": -73.7781},
                        {"name": "vehicle_type", "type": "string", "required": False, "description": "Vehicle fleet class: sedan, suv, ev, premium.", "example": "sedan"},
                    ],
                    "response_example": {
                        "recommended_departure_time": "2026-08-31T08:15:00",
                        "estimated_duration_minutes": 48.0,
                        "distance_miles": 18.4,
                        "fare_estimate": {
                            "min_fare": 58.50,
                            "max_fare": 74.00,
                            "currency": "USD",
                            "surge_multiplier": 1.18,
                            "basis": "computed"
                        }
                    },
                    "code_samples": {
                        "curl": 'curl -X POST "http://localhost:8000/api/mobility/departure-time" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"pickup_lat": 40.7580, "pickup_lon": -73.9855, "dropoff_lat": 40.6413, "dropoff_lon": -73.7781, "vehicle_type": "sedan"}\'',
                        "python": 'import requests\n\nres = requests.post("http://localhost:8000/api/mobility/departure-time", json={\n    "pickup_lat": 40.7580,\n    "pickup_lon": -73.9855,\n    "dropoff_lat": 40.6413,\n    "dropoff_lon": -73.7781,\n    "vehicle_type": "sedan"\n})\nprint(res.json())',
                        "typescript": 'const res = await fetch("http://localhost:8000/api/mobility/departure-time", {\n  method: "POST",\n  headers: { "Content-Type": "application/json" },\n  body: JSON.stringify({\n    pickup_lat: 40.7580,\n    pickup_lon: -73.9855,\n    dropoff_lat: 40.6413,\n    dropoff_lon: -73.7781,\n    vehicle_type: "sedan"\n  })\n});\nconst data = await res.json();\nconsole.log(data);',
                    }
                },
                {
                    "id": "get-traffic",
                    "method": "GET",
                    "path": "/api/context/traffic",
                    "summary": "Real-Time Traffic Bottlenecks",
                    "description": "Returns road congestion index and bridge/tunnel bottleneck factors.",
                    "parameters": [
                        {"name": "lat", "type": "float", "required": True, "description": "Latitude coordinate.", "example": 40.7580},
                        {"name": "lon", "type": "float", "required": True, "description": "Longitude coordinate.", "example": -73.9855},
                    ],
                    "response_example": {
                        "congestion_index": 1.25,
                        "status": "moderate_traffic",
                        "corridor": "Midtown Arterial Crossing"
                    },
                    "code_samples": {
                        "curl": 'curl "http://localhost:8000/api/context/traffic?lat=40.7580&lon=-73.9855"',
                        "python": 'import requests\nres = requests.get("http://localhost:8000/api/context/traffic", params={"lat": 40.7580, "lon": -73.9855})\nprint(res.json())',
                        "typescript": 'const res = await fetch("http://localhost:8000/api/context/traffic?lat=40.7580&lon=-73.9855");\nconst data = await res.json();',
                    }
                },
                {
                    "id": "get-zone-totals",
                    "method": "GET",
                    "path": "/marts/zone_demand_totals",
                    "summary": "Aggregated TLC Zone Totals",
                    "description": "Returns total pickup/dropoff volumes and average fares for all 263 official NYC taxi zones.",
                    "parameters": [],
                    "response_example": [
                        {"location_id": 161, "zone_name": "Midtown Center", "borough": "Manhattan", "total_trips": 42189000, "avg_fare": 22.40},
                        {"location_id": 132, "zone_name": "JFK Airport", "borough": "Queens", "total_trips": 31540000, "avg_fare": 62.80}
                    ],
                    "code_samples": {
                        "curl": 'curl "http://localhost:8000/marts/zone_demand_totals"',
                        "python": 'import requests\nres = requests.get("http://localhost:8000/marts/zone_demand_totals")\nprint(res.json())',
                        "typescript": 'const res = await fetch("http://localhost:8000/marts/zone_demand_totals");\nconst data = await res.json();',
                    }
                },
                {
                    "id": "ws-chat",
                    "method": "WebSocket",
                    "path": "/chat/stream",
                    "summary": "Streaming AI Analyst Chat",
                    "description": "Bidirectional WebSocket for conversational natural language to SQL queries.",
                    "parameters": [
                        {"name": "question", "type": "string", "required": True, "description": "User question.", "example": "What are the top 5 pickup zones by average fare?"}
                    ],
                    "response_example": {
                        "type": "done",
                        "payload": {
                            "answer": "Based on the marts:\n- Charleston/Tottenville: $95.01\n- Eltingville/Annadale: $89.81...",
                            "route": "numeric"
                        }
                    }
                }
            ],
        },
        {
            "id": "developer-guide",
            "title": "Developer Guide & SDKs",
            "description": "Client integration guides for Python, TypeScript, and cURL.",
            "sections": [
                {
                    "id": "python-integration",
                    "title": "Python SDK Integration",
                    "content": (
                        "### Using ATLAS with Python\n\n"
                        "Integrate ATLAS into your Python data pipelines with `requests` or `httpx`:\n\n"
                        "```python\n"
                        "import requests\n\n"
                        "BASE_URL = \"http://localhost:8000\"\n\n"
                        "def get_optimal_departure(pickup, dropoff, vehicle=\"sedan\"):\n"
                        "    payload = {\n"
                        "        \"pickup_lat\": pickup[0],\n"
                        "        \"pickup_lon\": pickup[1],\n"
                        "        \"dropoff_lat\": dropoff[0],\n"
                        "        \"dropoff_lon\": dropoff[1],\n"
                        "        \"vehicle_type\": vehicle\n"
                        "    }\n"
                        "    resp = requests.post(f\"{BASE_URL}/api/mobility/departure-time\", json=payload)\n"
                        "    resp.raise_for_status()\n"
                        "    return resp.json()\n\n"
                        "# Example: Times Square to JFK Airport\n"
                        "result = get_optimal_departure((40.7580, -73.9855), (40.6413, -73.7781))\n"
                        "print(\"Leave at:\", result[\"recommended_departure_time\"])\n"
                        "print(\"Duration:\", result[\"estimated_duration_minutes\"], \"minutes\")\n"
                        "print(\"Fare:\", result[\"fare_estimate\"][\"min_fare\"], \"USD\")\n"
                        "```"
                    ),
                },
                {
                    "id": "typescript-integration",
                    "title": "TypeScript & React Integration",
                    "content": (
                        "### Using ATLAS with TypeScript / React\n\n"
                        "```typescript\n"
                        "export async function estimateJourney(pickup: [number, number], dropoff: [number, number]) {\n"
                        "  const res = await fetch(\"http://localhost:8000/api/mobility/departure-time\", {\n"
                        "    method: \"POST\",\n"
                        "    headers: { \"Content-Type\": \"application/json\" },\n"
                        "    body: JSON.stringify({\n"
                        "      pickup_lat: pickup[0],\n"
                        "      pickup_lon: pickup[1],\n"
                        "      dropoff_lat: dropoff[0],\n"
                        "      dropoff_lon: dropoff[1],\n"
                        "      vehicle_type: \"sedan\"\n"
                        "    })\n"
                        "  });\n"
                        "  return res.json();\n"
                        "}\n"
                        "```"
                    ),
                }
            ],
        },
        {
            "id": "data-and-architecture",
            "title": "Data & Architecture",
            "description": "System architecture, 1.4B+ trip data vintage, and DuckDB marts.",
            "sections": [
                {
                    "id": "data-vintage",
                    "title": "Data Foundation",
                    "content": (
                        "### 1.4B+ Trip Data Foundation\n\n"
                        "- **Total Records**: Over 1,400,000,000 official NYC Taxi & Limousine Commission trips.\n"
                        "- **263 Taxi Zones**: Complete spatial polygon coverage across Manhattan, Brooklyn, Queens, Bronx, and Staten Island.\n"
                        "- **DuckDB Columnar Storage**: Vectorized in-process queries delivering sub-85ms execution without database locks."
                    ),
                },
                {
                    "id": "architecture-summary",
                    "title": "Dual-Core Engine Design",
                    "content": (
                        "### Analytical Core + Real-Time Context Engine\n\n"
                        "1. **DuckDB Analytics Marts**: Pre-aggregated hourly demand, fare percentiles, and zone pair flows.\n"
                        "2. **Real-Time Context Orchestrator**: Live weather, traffic bottlenecks, and public holiday modifiers.\n"
                        "3. **Neon PostgreSQL**: Cloud operational store for user history, sessions, and telemetry audit trails."
                    ),
                }
            ]
        }
    ]
}


@router.get("/spec")
def get_docs_spec() -> dict[str, Any]:
    """Returns the simplified, clean documentation specification JSON."""
    return DOCS_SPEC
