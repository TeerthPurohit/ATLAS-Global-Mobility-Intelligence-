import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Database, Table } from "lucide-react";
import { fetchWarehouseTables } from "../api/client";

export const Warehouse: React.FC = () => {
  const { data: tables, isLoading } = useQuery({ queryKey: ["warehouse-tables"], queryFn: fetchWarehouseTables });
  const [selectedTableName, setSelectedTableName] = useState<string | null>(null);

  const selectedTable = tables?.find((t) => t.table === selectedTableName) ?? tables?.[0];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <Database className="w-5 h-5 text-brand-400" />
          DuckDB Warehouse Explorer
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Live schema introspection (DESCRIBE + COUNT) against data/warehouse/nyc_rides.duckdb via GET /warehouse/tables
        </p>
      </div>

      {isLoading || !tables ? (
        <div className="py-16 text-center text-xs text-slate-500">Querying warehouse schema...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Table Selector List */}
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 px-2 font-mono">Warehouse Tables</h3>
            {tables.map((t) => (
              <button
                key={t.table}
                onClick={() => setSelectedTableName(t.table)}
                className={`w-full p-3 rounded-lg text-left text-xs font-medium transition-colors flex items-center justify-between ${
                  selectedTable?.table === t.table
                    ? "bg-brand-600/20 text-brand-400 border border-brand-500/30"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Table className="w-4 h-4 text-slate-400" />
                  <span className="font-mono">{t.table}</span>
                </div>
              </button>
            ))}
          </div>

          {/* Schema Table */}
          {selectedTable && (
            <div className="lg:col-span-3 p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div>
                    <h2 className="text-sm font-bold font-mono text-slate-100">{selectedTable.table}</h2>
                    <p className="text-xs text-slate-400 font-mono">{selectedTable.row_count.toLocaleString()} rows</p>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-brand-500/10 text-brand-400 font-mono border border-brand-500/20 font-semibold">
                    Live DESCRIBE
                  </span>
                </div>

                <div className="overflow-x-auto mt-4">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px] font-mono">
                      <tr>
                        <th className="p-3">Column Name</th>
                        <th className="p-3">Data Type</th>
                        <th className="p-3">Nullable</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {selectedTable.columns.map((c) => (
                        <tr key={c.column_name} className="hover:bg-slate-800/40">
                          <td className="p-3 font-mono font-medium text-brand-400">{c.column_name}</td>
                          <td className="p-3 font-mono text-emerald-400">{c.column_type}</td>
                          <td className="p-3 text-slate-400">{c.null}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Component Provenance Footer */}
              <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Source: <strong className="text-brand-400">GET /warehouse/tables</strong></span>
                <span className="text-slate-500">data/warehouse/nyc_rides.duckdb</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
