"""Per-station insight paragraphs for London's Santander Cycles data --
London's counterpart to generate_insight_docs.py (NYC), closing the gap
noted in backend/registry/cities.py: London has a real warehouse (846K+
real journeys) but no insight-doc corpus, so it's stuck on `sql_only` chat
tier with explanatory questions refused even though real data exists to
ground an answer.

Every number in the output traces to one of:
- `london_station_hourly_demand` mart (trip volume, avg trip duration, busiest hours)
- `int_london_journeys_enriched` (top outbound destination station, aggregated directly --
  bike-share has no zone_pair_flows-equivalent mart, so this groups the enriched table itself)
- `algorithms/graph/pagerank_hubs.py` power iteration over a station-to-station
  flow graph built inline here (build_zone_graph.py is NYC's zone_pair_flows table
  by name -- London's journeys aggregate into the same nx.DiGraph shape without
  needing a shared/modified builder)

No fare field: Santander Cycles is a bike-share system, not a metered ride --
unlike NYC's insight docs there is no avg_fare fact here, and the LLM system
prompt below never mentions one, so it can't hallucinate a price. Same
grounding contract as generate_insight_docs.py otherwise: the LLM only ever
turns an already-computed fact list into a short paragraph, and
validate_grounding() (reused from there, not duplicated) rejects any
paragraph introducing a number not traceable to the fact list.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_insight_docs import extract_numbers, validate_grounding  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import OPENAI_MODEL  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "warehouse" / "london_cycles.duckdb"
OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "london_insight_docs.jsonl"

SYSTEM_PROMPT = """You write one short, plain-language paragraph (3-5 sentences) \
describing a London Santander Cycles docking station, for a chat answer.

Rules, no exceptions:
- Use ONLY the numbers given in the fact list below, and use them EXACTLY as \
given (same digits, same rounding). Never round, convert, sum, average, or \
otherwise compute a new number.
- Do not introduce any statistic, ranking, date, or comparison that is not \
explicitly in the fact list.
- Do not mention a fare or price -- this is a bike-share system, there is none.
- Write hours in 24-hour form exactly as given (e.g. "18:00"), never converted \
to am/pm.
- No markdown, no bullet points, no headers -- plain prose only.
"""


def _build_station_flow_graph(journeys: pd.DataFrame) -> nx.DiGraph:
    flows = (
        journeys[journeys["start_station_id"] != journeys["end_station_id"]]
        .groupby(["start_station_id", "end_station_id"]).size().reset_index(name="weight")
    )
    graph = nx.DiGraph()
    for row in flows.itertuples(index=False):
        graph.add_edge(row.start_station_id, row.end_station_id, weight=float(row.weight))
    return graph


def _facts_for_station(station_id: str, station_name: str, hourly: pd.DataFrame,
                        journeys: pd.DataFrame, rank_info: dict) -> dict:
    total_trips = int(hourly["total_trips"].sum())
    avg_duration = (
        float((hourly["avg_duration_min"] * hourly["total_trips"]).sum() / total_trips) if total_trips else None
    )

    by_hour = hourly.groupby("hour")["total_trips"].sum().sort_values(ascending=False)
    top_hours = [
        {
            "hour": int(hour),
            "total_trips": int(trips),
            "share_pct": round(float(trips) / total_trips * 100, 1) if total_trips else 0.0,
        }
        for hour, trips in by_hour.head(3).items()
    ]

    outbound = journeys[journeys["start_station_id"] == station_id]
    dest_counts = outbound[outbound["end_station_id"] != station_id]["end_station_name"].value_counts()
    top_destination = (
        {"station": str(dest_counts.index[0]), "trip_count": int(dest_counts.iloc[0])}
        if len(dest_counts) else None
    )

    return {
        "station_id": station_id,
        "station_name": station_name,
        "total_trips": total_trips,
        "avg_duration_min": round(avg_duration, 1) if avg_duration is not None else None,
        "top_hours": top_hours,
        "top_destination": top_destination,
        "pagerank_rank": rank_info.get("rank"),
        "pagerank_score": rank_info.get("score"),
        "pagerank_total_stations": rank_info.get("total_stations"),
        "sources": {
            "demand": "mart:london_station_hourly_demand",
            "flows": "int_london_journeys_enriched (aggregated start/end station pairs)",
            "hub_rank": "algorithms/graph/pagerank_hubs.py (power iteration over a station "
            "flow graph built from int_london_journeys_enriched)",
        },
    }


def _allowed_numbers(facts: dict) -> set[float]:
    allowed = set()
    for key in ("station_id", "total_trips", "avg_duration_min", "pagerank_rank", "pagerank_total_stations"):
        if facts.get(key) is not None:
            try:
                allowed.add(float(facts[key]))
            except ValueError:
                continue  # station_id is occasionally non-numeric
    for h in facts["top_hours"]:
        allowed.update({float(h["hour"]), float(h["total_trips"]), float(h["share_pct"])})
    if facts["top_destination"]:
        allowed.add(float(facts["top_destination"]["trip_count"]))
    return allowed


def _template_sentence(facts: dict) -> str:
    if facts["total_trips"]:
        parts = [
            f"{facts['station_name']} recorded {facts['total_trips']:,} trips in the observed period, "
            f"averaging {facts['avg_duration_min']:.1f} minutes per ride."
        ]
    else:
        parts = [f"{facts['station_name']} has not yet measured trips."]

    if facts["top_hours"]:
        h = facts["top_hours"][0]
        parts.append(
            f"Its busiest hour is {h['hour']:02d}:00, with {h['total_trips']:,} trips "
            f"({h['share_pct']:.1f}% of the station's total)."
        )
    if facts["pagerank_rank"] is not None:
        parts.append(
            f"By PageRank hub importance, it ranks {facts['pagerank_rank']} of "
            f"{facts['pagerank_total_stations']} stations."
        )
    else:
        parts.append("PageRank hub importance for this station has not yet been measured.")
    if facts["top_destination"]:
        d = facts["top_destination"]
        parts.append(f"Its top outbound destination is {d['station']}, with {d['trip_count']:,} trips recorded.")
    else:
        parts.append("No outbound station-pair flow has been recorded for this station yet.")
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
        print(f"  [warn] LLM phrasing failed for {facts['station_name']} ({exc}); using template", file=sys.stderr)
        return None

    if not text or not validate_grounding(text, _allowed_numbers(facts)):
        print(f"  [warn] LLM output for {facts['station_name']} failed grounding check; using template", file=sys.stderr)
        return None
    return text


def load_insight_docs(path: Path = OUTPUT_PATH) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_all(db_path: Path = DEFAULT_DB_PATH, output_path: Path = OUTPUT_PATH, use_llm: bool = True) -> list[dict]:
    from algorithms.graph.pagerank_hubs import pagerank

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        hourly = con.execute(
            "SELECT station_id, station_name, hour, total_trips, avg_duration_min FROM london_station_hourly_demand"
        ).df()
        journeys = con.execute(
            "SELECT start_station_id, end_station_id, end_station_name FROM int_london_journeys_enriched"
        ).df()
    finally:
        con.close()

    graph = _build_station_flow_graph(journeys)
    scores = pagerank(graph)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    rank_by_station = {sid: i + 1 for i, (sid, _) in enumerate(ranked)}
    score_by_station = dict(scores)
    total_stations = len(ranked)

    stations = hourly[["station_id", "station_name"]].drop_duplicates()

    docs = []
    n_llm, n_template = 0, 0
    for row in stations.itertuples(index=False):
        station_id, station_name = row.station_id, row.station_name
        station_hourly = hourly[hourly["station_id"] == station_id]
        rank_info = {
            "rank": rank_by_station.get(station_id),
            "score": score_by_station.get(station_id),
            "total_stations": total_stations,
        }
        facts = _facts_for_station(station_id, station_name, station_hourly, journeys, rank_info)

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

    print(f"wrote {len(docs)} London insight docs to {output_path} ({n_llm} llm-phrased, {n_template} template fallback)")
    return docs


def demo() -> None:
    docs = generate_all()
    assert len(docs) > 0, "must generate at least one insight doc"
    for doc in docs:
        assert validate_grounding(doc["text"], _allowed_numbers(doc)), (
            f"ungrounded number slipped through for {doc['station_name']}"
        )
    sample = docs[0]
    print(f"\nsample doc ({sample['station_name']}, phrased_by={sample['phrased_by']}):\n{sample['text']}")


if __name__ == "__main__":
    demo()
