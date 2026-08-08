"use client";

import { useEffect, useState } from "react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { API_BASE_URL } from "@/lib/api";

type Units = "miles" | "km";
type Theme = "dark" | "light";

const UNITS_KEY = "jie:units";
const THEME_KEY = "jie:theme";

export default function SettingsPage() {
  const [units, setUnits] = useState<Units>("miles");
  const [theme, setTheme] = useState<Theme>("dark");

  // Load saved prefs on mount (localStorage isn't available during SSR).
  useEffect(() => {
    const savedUnits = localStorage.getItem(UNITS_KEY) as Units | null;
    const savedTheme = (document.documentElement.getAttribute("data-theme") as Theme | null) ?? "dark";
    if (savedUnits) setUnits(savedUnits);
    setTheme(savedTheme);
  }, []);

  function handleUnitsChange(next: Units) {
    setUnits(next);
    localStorage.setItem(UNITS_KEY, next);
  }

  function handleThemeChange(next: Theme) {
    setTheme(next);
    localStorage.setItem(THEME_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="font-display text-2xl tracking-wide text-ink-primary">Settings</h1>

      <Card>
        <CardTitle className="font-display text-base tracking-wide">Display</CardTitle>
        <div className="mt-4 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs uppercase tracking-wider text-ink-muted">Units</span>
            <Select
              value={units}
              onChange={(e) => handleUnitsChange(e.target.value as Units)}
              className="max-w-xs"
            >
              <option value="miles">Miles</option>
              <option value="km">Kilometers</option>
            </Select>
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs uppercase tracking-wider text-ink-muted">Theme</span>
            <Select
              value={theme}
              onChange={(e) => handleThemeChange(e.target.value as Theme)}
              className="max-w-xs"
            >
              <option value="dark">Dark (instrument panel)</option>
              <option value="light">Light (parchment)</option>
            </Select>
          </label>

          <div className="flex flex-col gap-1.5">
            <span className="text-xs uppercase tracking-wider text-ink-muted">Currency</span>
            <span className="font-mono text-sm text-ink-primary">USD — the only currency this platform prices in (NYC data only)</span>
          </div>
        </div>
      </Card>

      <Card>
        <CardTitle className="font-display text-base tracking-wide">API</CardTitle>
        <div className="mt-4 flex flex-col gap-1.5">
          <span className="text-xs uppercase tracking-wider text-ink-muted">Base URL</span>
          <span className="font-mono text-sm text-ink-secondary">{API_BASE_URL}</span>
          <span className="text-xs text-ink-muted">
            Read-only. Set NEXT_PUBLIC_API_BASE_URL and restart to change it.
          </span>
        </div>
      </Card>
    </div>
  );
}
