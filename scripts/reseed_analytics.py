import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv()

from backend.services.prediction_log import get_engine, TABLE_NAME, log_prediction, init_db

def main():
    engine = get_engine()
    init_db()
    with engine.begin() as conn:
        conn.exec_driver_sql(f'DELETE FROM "{TABLE_NAME}"')
    print("Cleaned old legacy rows from prediction log.")

    samples = [
        (40.6720, -73.9455, 40.7016, -73.9221, "Crown Heights North ➔ Bushwick North", "sedan", 23.50, 76, 3.2, 11),
        (40.6413, -74.0158, 40.6413, -73.7781, "Sunset Park ➔ JFK Airport", "sedan", 84.71, 93, 14.9, 32),
        (40.7580, -73.9855, 40.7772, -73.8730, "Midtown Times Sq ➔ LaGuardia Airport", "sedan", 48.20, 89, 9.4, 26),
        (40.7128, -74.0060, 40.7033, -73.9903, "Financial District ➔ DUMBO Brooklyn", "ev", 21.80, 84, 2.8, 10),
        (40.7831, -73.9665, 40.7484, -73.9857, "Upper East Side ➔ Empire State", "sedan", 19.40, 88, 2.9, 14),
        (40.6782, -73.9681, 40.7282, -73.9400, "Prospect Heights ➔ Greenpoint", "sedan", 27.60, 85, 4.6, 18),
        (40.8115, -73.9465, 40.7580, -73.9855, "Harlem 125th ➔ Times Square", "suv", 36.90, 87, 5.8, 22),
    ]

    now = datetime.now(timezone.utc)
    for i, (plat, plon, dlat, dlon, name, vtype, fare, conf, dist, dur) in enumerate(samples):
        req_time = (now - timedelta(minutes=i * 18 + 5)).isoformat()
        resp = {
            "city_id": "nyc",
            "route_name": name,
            "fare": {
                "value": fare,
                "basis": "modeled_estimate",
                "confidence": conf / 100,
                "mae": 6.78,
                "error_band": [round(fare - 6.78, 2), round(fare + 6.78, 2)],
            },
            "distance": {"value": dist, "unit": "miles", "basis": "computed"},
            "duration": {"value": dur, "unit": "mins", "basis": "computed"},
            "confidence": {"value": conf, "unit": "percent", "basis": "computed"},
        }
        log_prediction(plat, plon, dlat, dlon, req_time, vtype, resp)
    print(f"Successfully re-seeded {len(samples)} calibrated audit log records!")

if __name__ == "__main__":
    main()
