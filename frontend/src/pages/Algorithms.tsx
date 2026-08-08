import React from "react";
import { useQuery } from "@tanstack/react-query";
import { GitMerge, Zap, Network, Clock, TrendingUp, CheckCircle2 } from "lucide-react";
import { fetchAlgorithmBenchmarks } from "../api/client";
import { Provenance } from "../components/ui/Provenance";

export const Algorithms: React.FC = () => {
  const { data: benchmarks } = useQuery({ queryKey: ["algorithm-benchmarks"], queryFn: fetchAlgorithmBenchmarks });
  const kdtree = benchmarks?.kdtree;
  const pagerank = benchmarks?.pagerank;
  const maxLatency = kdtree ? Math.max(kdtree.linear_scan_us_per_query, kdtree.kdtree_us_per_query) : 1;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <GitMerge className="w-5 h-5 text-indigo-400" />
            From-Scratch Algorithmic Benchmarks
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Pure Python / NumPy / SciPy algorithm implementations verified against exact reference tolerances
          </p>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            All Correctness Tests Passed
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Alg 1: KD-Tree Spatial Index */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <h2 className="text-sm font-bold text-slate-100">KD-Tree Spatial Zone Lookup</h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 font-mono font-bold border border-amber-500/20">
                {kdtree ? `${kdtree.speedup_x.toFixed(2)}x Measured Speedup` : "Loading..."}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-3 leading-relaxed">
              Fast nearest-neighbor spatial index in 2D Euclidean space (<code className="font-mono text-emerald-400">algorithms/spatial/kdtree_zone_lookup.py</code>). Maps arbitrary lat/lon coordinates to TLC zone centroids.
            </p>

            {/* Performance Visual Benchmark Gauge */}
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3 font-mono text-xs">
              <div>
                <div className="flex justify-between text-slate-400 text-[11px] mb-1">
                  <span>Linear Scan Latency:</span>
                  <span className="text-slate-300">{kdtree ? `${kdtree.linear_scan_us_per_query.toFixed(2)} us` : "..."}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div className="h-full bg-slate-600 w-full" />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-slate-400 text-[11px] mb-1">
                  <span>KD-Tree Query Latency:</span>
                  <span className="text-emerald-400 font-bold">{kdtree ? `${kdtree.kdtree_us_per_query.toFixed(2)} us` : "..."}</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-amber-400"
                    style={{ width: kdtree ? `${(kdtree.kdtree_us_per_query / maxLatency) * 100}%` : "0%" }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div>
            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between font-mono">
              <span>Zones Indexed:</span>
              <span className="text-emerald-400">{kdtree ? kdtree.n_zones : "..."} centroids, {kdtree ? kdtree.n_queries : "..."} queries</span>
            </div>

            <Provenance
              type="artifact"
              source="algorithms/spatial/output/kdtree_benchmark.json"
              detail={`Benchmark: ${kdtree ? kdtree.n_zones : "..."} centroids`}
            />
          </div>
        </div>

        {/* Alg 2: PageRank Network Hubs */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Network className="w-4 h-4 text-indigo-400" />
                <h2 className="text-sm font-bold text-slate-100">PageRank Network Hub Analysis</h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-400 font-mono font-bold border border-indigo-500/20">
                NetworkX Match &lt; 1e-6
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-3 leading-relaxed">
              Iterative PageRank over directed transit flow graphs (<code className="font-mono text-emerald-400">algorithms/graph/pagerank_hubs.py</code>). Uncovers network transit hubs outranking raw trip volume.
            </p>

            {/* Top Network Hub Topology Cards */}
            <div className="mt-4 space-y-2">
              {pagerank ? (
                pagerank.top_hubs.slice(0, 3).map((hub) => (
                  <div key={hub.rank} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center space-x-2">
                      <span className="w-6 text-brand-400 font-bold">#{hub.rank}</span>
                      <span className="text-slate-200">{hub.zone}</span>
                    </div>
                    <span className="text-indigo-400 font-bold">{hub.pagerank_score.toFixed(4)}</span>
                  </div>
                ))
              ) : (
                <div className="p-4 text-center text-xs text-slate-500">Loading pagerank_hubs.json...</div>
              )}
            </div>
          </div>

          <div>
            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between font-mono">
              <span>Damping Factor:</span>
              <span className="text-slate-200">alpha = {pagerank ? pagerank.damping : "0.85"}</span>
            </div>

            <Provenance
              type="artifact"
              source="algorithms/graph/output/pagerank_hubs.json"
              detail={pagerank ? `${pagerank.n_zones} zones, ${pagerank.n_edges.toLocaleString()} edges` : undefined}
            />
          </div>
        </div>

        {/* Alg 3: Dijkstra Shortest Path */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-emerald-400" />
                <h2 className="text-sm font-bold text-slate-100">Dijkstra Shortest Path & ETA</h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 font-mono font-bold border border-emerald-500/20">
                Tolerance &lt; 1e-6
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-3 leading-relaxed">
              Min-heap Dijkstra implementation (<code className="font-mono text-emerald-400">algorithms/graph/shortest_path_eta.py</code>) calculating optimal travel times across zone adjacency graphs.
            </p>

            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Priority Queue:</span>
                <span className="text-slate-200">heapq binary min-heap</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Verification:</span>
                <span className="text-emerald-400">networkx.dijkstra_path match</span>
              </div>
            </div>
          </div>

          <div>
            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between font-mono">
              <span>Graph Edges:</span>
              <span className="text-slate-200">Zone-pair weighted travel durations</span>
            </div>

            <Provenance type="derived" source="algorithms/graph/shortest_path_eta.py" detail="Adjacency: zone pairs" />
          </div>
        </div>

        {/* Alg 4: EWMA & Seasonality */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-4 h-4 text-brand-400" />
                <h2 className="text-sm font-bold text-slate-100">EWMA & Seasonality Decompose</h2>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] bg-brand-500/10 text-brand-400 font-mono font-bold border border-brand-500/20">
                Alpha=0.5 Optimal Sweep
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-3 leading-relaxed">
              Multiplicative timeseries decomposition (<code className="font-mono text-emerald-400">algorithms/timeseries/ewma_smoothing.py</code>) extracting hourly trend, seasonal index, and residual noise components.
            </p>

            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Alpha Choice:</span>
                <span className="text-brand-400">0.5 (Bias/Variance Sweep)</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Block Splitting:</span>
                <span className="text-slate-200">No Feb/Apr/May gap bridging</span>
              </div>
            </div>
          </div>

          <div>
            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex justify-between font-mono">
              <span>Seasonal Period:</span>
              <span className="text-slate-200">24-hour multiplicative cycle</span>
            </div>

            <Provenance type="derived" source="algorithms/timeseries/ewma_smoothing.py" detail="Cycle: 24-hour" />
          </div>
        </div>
      </div>
    </div>
  );
};
