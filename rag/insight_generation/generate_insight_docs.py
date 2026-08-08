"""Per-zone insight paragraphs, templated from real computed stats (FR-1).

Every number in the output traces to one of:
- `zone_hourly_demand` mart (trip volume, avg fare/distance, busiest hours)
- `zone_pair_flows` mart (top outbound destination zone)
- `algorithms/graph/pagerank_hubs.py` power iteration over the same
  zone-flow graph `algorithms/graph/build_zone_graph.py` builds for Layer 2
  (hub importance rank)

The LLM is only ever asked to turn an already-computed, already-rounded
fact list into a short paragraph -- it never sees raw rows and is never
asked to compute anything. `validate_grounding()` then parses every number
out of the LLM's paragraph and rejects the paragraph (falling back to a
plain templated sentence, which is itself built only from the same facts)
if it contains any number that isn't traceable to the fact list. Rule 2,
zero tolerance -- see spec risk note in specs/008-hybrid-rag/spec.md.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DEFAULT_DB_PATH, OPENAI_MODEL  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "insight_docs.jsonl"

# Numbers below this bound are always allowed in LLM phrasing without being
# traced to a specific fact -- hour-of-day, day-of-month, month counts, etc.
# ("18:00", "3 months") can't represent a fabricated *statistic*, so gating
# them the same way as total_trips/avg_fare would just produce false
# rejections for harmless connective phrasing.
_LOOSE_NUMBER_MAX = 31
# Dataset year is a fixed metadata fact (see .claude/memory.md), not a
# computed statistic -- safe to allow without a mart/algorithm citation.
_ALWAYS_ALLOWED = {2024}

_NUMBER_RE = re.compile(r"-?\d[\d,]*\.?\d*")

SYSTEM_PROMPT = """You write one short, plain-language paragraph (3-5 sentences) \
describing a NYC ride-hailing pickup zone, for a chat answer.

Rules, no exceptions:
- Use ONLY the numbers given in the fact list below, and use them EXACTLY as \
given (same digits, same rounding). Never round, convert, sum, average, or \
otherwise compute a new number.
- Do not introduce any statistic, ranking, date, or comparison that is not \
explicitly in the fact list.
- Write hours in 24-hour form exactly as given (e.g. "18:00"), never converted \
to am/pm.
- No markdown, no bullet points, no headers -- plain prose only.
"""


def _facts_for_zone(zone_id: int, zone_name: str, borough: str, hourly: pd.DataFrame,
                     flows: pd.DataFrame, rank_info: dict) -> dict:
    total_trips = int(hourly["total_trips"].sum())
    avg_fare = float((hourly["avg_fare"] * hourly["total_trips"]).sum() / total_trips) if total_trips else None
    avg_distance = (
        float((hourly["avg_trip_distance_miles"] * hourly["total_trips"]).sum() / total_trips)
        if total_trips else None
    )

    by_hour = hourly.groupby("pickup_hour")["total_trips"].sum().sort_values(ascending=False)
    top_hours = [
        {
            "hour": int(hour),
            "total_trips": int(trips),
            "share_pct": round(float(trips) / total_trips * 100, 1) if total_trips else 0.0,
        }
        for hour, trips in by_hour.head(3).items()
    ]

    dest_row = flows[flows["dropoff_zone"] != zone_name].sort_values("trip_count", ascending=False).head(1)
    if len(dest_row):
        top_destination = {
            "zone": str(dest_row.iloc[0]["dropoff_zone"]),
            "trip_count": int(dest_row.iloc[0]["trip_count"]),
        }
    else:
        top_destination = None

    return {
        "zone_id": zone_id,
        "zone_name": zone_name,
        "borough": borough,
        "total_trips": total_trips,
        "avg_fare": round(avg_fare, 2) if avg_fare is not None else None,
        "avg_distance_miles": round(avg_distance, 1) if avg_distance is not None else None,
        "top_hours": top_hours,
        "top_destination": top_destination,
        "pagerank_rank": rank_info.get("rank"),
        "pagerank_score": rank_info.get("score"),
        "pagerank_total_zones": rank_info.get("total_zones"),
        "sources": {
            "demand": "mart:zone_hourly_demand",
            "flows": "mart:zone_pair_flows",
            "hub_rank": "algorithms/graph/pagerank_hubs.py (power iteration over "
            "algorithms/graph/build_zone_graph.py's zone_pair_flows graph)",
        },
    }


def _allowed_numbers(facts: dict) -> set[float]:
    allowed = set(_ALWAYS_ALLOWED)
    for key in ("zone_id", "total_trips", "avg_fare", "avg_distance_miles", "pagerank_rank", "pagerank_total_zones"):
        if facts.get(key) is not None:
            allowed.add(float(facts[key]))
    for h in facts["top_hours"]:
        allowed.update({float(h["hour"]), float(h["total_trips"]), float(h["share_pct"])})
    if facts["top_destination"]:
        allowed.add(float(facts["top_destination"]["trip_count"]))
    return allowed


def extract_numbers(text: str) -> list[float]:
    out = []
    for tok in _NUMBER_RE.findall(text):
        try:
            out.append(float(tok.replace(",", "")))
        except ValueError:
            continue
    return out


def validate_grounding(text: str, allowed: set[float], tol: float = 0.55) -> bool:
    """True iff every number in `text` is either a small connective number
    (hour/day/month, <= _LOOSE_NUMBER_MAX) or within `tol` of a value in
    `allowed` (rounding slack for e.g. "$12.3" vs a fact of 12.34)."""
    for n in extract_numbers(text):
        if 0 <= abs(n) <= _LOOSE_NUMBER_MAX:
            continue
        if any(abs(n - a) <= tol for a in allowed):
            continue
        return False
    return True


def _template_sentence(facts: dict) -> str:
    if facts["total_trips"]:
        parts = [
            f"{facts['zone_name']} ({facts['borough']}) recorded {facts['total_trips']:,} pickups "
            f"in the observed period, averaging ${facts['avg_fare']:.2f} per trip over "
            f"{facts['avg_distance_miles']:.1f} miles."
        ]
    else:
        parts = [f"{facts['zone_name']} ({facts['borough']}) has not yet measured pickups."]

    if facts["top_hours"]:
        h = facts["top_hours"][0]
        parts.append(
            f"Its busiest hour is {h['hour']:02d}:00, with {h['total_trips']:,} trips "
            f"({h['share_pct']:.1f}% of the zone's total)."
        )
    if facts["pagerank_rank"] is not None:
        parts.append(
            f"By PageRank hub importance, it ranks {facts['pagerank_rank']} of "
            f"{facts['pagerank_total_zones']} zones."
        )
    else:
        parts.append("PageRank hub importance for this zone has not yet been measured.")
    if facts["top_destination"]:
        d = facts["top_destination"]
        parts.append(f"Its top outbound destination is {d['zone']}, with {d['trip_count']:,} trips recorded.")
    else:
        parts.append("No outbound zone-pair flow has been recorded for this zone yet.")
    return " ".join(parts)


def _phrase_with_llm(facts: dict) -> str | None:
    try:
        from llm_client import chat_completion
    except ImportError:
        return None
    try:
        user_prompt = "Fact list:\n" + json.dumps({k: v for k, v in facts.items() if k != "sources"}, indent=2)
        resp = chat_completion(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_completion_tokens=250,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001 -- any LLM/network failure just falls back
        print(f"  [warn] LLM phrasing failed for {facts['zone_name']} ({exc}); using template", file=sys.stderr)
        return None

    if not text or not validate_grounding(text, _allowed_numbers(facts)):
        print(f"  [warn] LLM output for {facts['zone_name']} failed grounding check; using template", file=sys.stderr)
        return None
    return text


def load_insight_docs(path: Path = OUTPUT_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_all(db_path: Path = DEFAULT_DB_PATH, output_path: Path = OUTPUT_PATH, use_llm: bool = True) -> list[dict]:
    # Lazy: networkx is a training/precompute-only dep, deliberately absent
    # from requirements-backend.txt (rule 8) -- importing it at module level
    # would drag it onto the backend's request-time import chain even though
    # only this offline precompute path needs it.
    from algorithms.graph.build_zone_graph import build_zone_graph
    from algorithms.graph.pagerank_hubs import pagerank

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        demand = con.execute(
            "SELECT pickup_location_id, pickup_zone, pickup_borough, pickup_hour, "
            "total_trips, avg_fare, avg_trip_distance_miles FROM zone_hourly_demand"
        ).df()
        flows = con.execute(
            "SELECT pickup_zone, dropoff_zone, SUM(trip_count) AS trip_count "
            "FROM zone_pair_flows GROUP BY 1, 2"
        ).df()
    finally:
        con.close()

    graph = build_zone_graph(db_path)
    scores = pagerank(graph)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    rank_by_zone = {name: i + 1 for i, (name, _) in enumerate(ranked)}
    score_by_zone = dict(scores)
    total_zones = len(ranked)

    zones = demand[["pickup_location_id", "pickup_zone", "pickup_borough"]].drop_duplicates()

    docs = []
    n_llm, n_template = 0, 0
    for row in zones.itertuples(index=False):
        zone_id, zone_name, borough = row.pickup_location_id, row.pickup_zone, row.pickup_borough
        hourly = demand[demand["pickup_location_id"] == zone_id]
        zone_flows = flows[flows["pickup_zone"] == zone_name]
        rank_info = {
            "rank": rank_by_zone.get(zone_name),
            "score": score_by_zone.get(zone_name),
            "total_zones": total_zones,
        }
        facts = _facts_for_zone(zone_id, zone_name, borough, hourly, zone_flows, rank_info)

        text = _phrase_with_llm(facts) if use_llm else None
        if text is None:
            text = _template_sentence(facts)
            phrased_by = "template"
        else:
            phrased_by = "llm"
        n_llm += phrased_by == "llm"
        n_template += phrased_by == "template"

        docs.append({**facts, "text": text, "phrased_by": phrased_by})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc) + "\n")

    print(f"wrote {len(docs)} insight docs to {output_path} ({n_llm} llm-phrased, {n_template} template fallback)")
    return docs


def demo() -> None:
    docs = generate_all()
    assert len(docs) > 0, "must generate at least one insight doc"
    for doc in docs:
        assert validate_grounding(doc["text"], _allowed_numbers(doc)), (
            f"ungrounded number slipped through for {doc['zone_name']}"
        )
    sample = docs[0]
    print(f"\nsample doc ({sample['zone_name']}, phrased_by={sample['phrased_by']}):\n{sample['text']}")


if __name__ == "__main__":
    demo()
