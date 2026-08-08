import React, { useState } from "react";
import { Settings as SettingsIcon, CheckCircle2 } from "lucide-react";
import { API_BASE_URL } from "../api/client";

export const Settings: React.FC = () => {
  const [apiBaseUrl, setApiBaseUrl] = useState<string>(API_BASE_URL);
  const [saved, setSaved] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    localStorage.setItem("app_api_base_url", apiBaseUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-brand-400" />
          Application Settings
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Local client preferences and backend service connection parameters
        </p>
      </div>

      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">FastAPI Backend URL</label>
            <input
              type="text"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500 font-mono"
            />
            <p className="text-[11px] text-slate-500 mt-1">
              This actually overrides the API client -- reload the page after saving for it to take effect.
            </p>
          </div>

          <div className="pt-4 flex items-center space-x-3 border-t border-slate-800">
            <button
              type="submit"
              className="py-2.5 px-5 rounded-lg bg-brand-500 hover:bg-brand-400 text-slate-950 text-xs font-semibold shadow-lg shadow-brand-500/20 transition-all"
            >
              Save & Apply
            </button>
            {saved && (
              <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                <CheckCircle2 className="w-4 h-4" /> Saved -- reload to apply.
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};
