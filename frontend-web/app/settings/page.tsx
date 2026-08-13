"use client";

import { useEffect, useState } from "react";
import { Card, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { API_BASE_URL } from "@/lib/api";
import { Sliders, Palette, Code } from "lucide-react";

type Units = "miles" | "km";
type Theme = "dark" | "light";

const UNITS_KEY = "jie:units";
const THEME_KEY = "jie:theme";

export default function SettingsPage() {
  const [units, setUnits] = useState<Units>("miles");
  const [theme, setTheme] = useState<Theme>("dark");

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
    <div className="flex flex-col gap-12">
      {/* Header */}
      <section className="flex flex-col gap-3">
        <span className="font-label-sm text-brass tracking-wider">
          Configuration
        </span>
        <h1 className="font-display-lg text-ink-primary">
          Settings
        </h1>
        <p className="font-body-md max-w-2xl text-ink-secondary">
          Customize your display preferences, units, and API configuration.
        </p>
      </section>

      {/* Display Settings */}
      <Card className="p-8">
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 bg-brass/10 rounded-sm">
            <Sliders className="h-5 w-5 text-brass" />
          </div>
          <div>
            <CardTitle className="font-section-lg">Display Preferences</CardTitle>
            <p className="font-body-sm text-ink-secondary mt-1">Customize how information is displayed</p>
          </div>
        </div>

        <div className="separator-line mb-6" />

        <div className="flex flex-col gap-6">
          {/* Units */}
          <div className="flex flex-col gap-2">
            <label className="font-section-md text-ink-primary">Distance Units</label>
            <Select
              value={units}
              onChange={(e) => handleUnitsChange(e.target.value as Units)}
              className="max-w-xs"
            >
              <option value="miles">Miles</option>
              <option value="km">Kilometers</option>
            </Select>
            <p className="font-body-sm text-ink-secondary mt-1">Choose your preferred distance measurement</p>
          </div>

          {/* Theme */}
          <div className="flex flex-col gap-2">
            <label className="font-section-md text-ink-primary">Theme</label>
            <Select
              value={theme}
              onChange={(e) => handleThemeChange(e.target.value as Theme)}
              className="max-w-xs"
            >
              <option value="dark">Dark (Instrument Panel)</option>
              <option value="light">Light (Parchment)</option>
            </Select>
            <p className="font-body-sm text-ink-secondary mt-1">Select your preferred color scheme</p>
          </div>

          {/* Currency */}
          <div className="flex flex-col gap-2">
            <label className="font-section-md text-ink-primary">Currency</label>
            <div className="font-body-md text-ink-primary">USD</div>
            <p className="font-body-sm text-ink-secondary mt-1">Prices display in each city&apos;s own currency (see formatCurrency)</p>
          </div>
        </div>
      </Card>

      {/* API Configuration */}
      <Card className="p-8">
        <div className="flex items-start gap-4 mb-6">
          <div className="p-3 bg-verdigris/10 rounded-sm">
            <Code className="h-5 w-5 text-verdigris" />
          </div>
          <div>
            <CardTitle className="font-section-lg">API Configuration</CardTitle>
            <p className="font-body-sm text-ink-secondary mt-1">Backend service endpoint</p>
          </div>
        </div>

        <div className="separator-line mb-6" />

        <div className="flex flex-col gap-3">
          <label className="font-section-md text-ink-primary">Base URL</label>
          <div className="bg-surface-0 border border-surface-border p-4 rounded-sm font-mono text-sm text-ink-secondary break-all">
            {API_BASE_URL}
          </div>
          <p className="font-body-sm text-ink-secondary mt-1">
            Read-only. Set <span className="font-mono text-brass">NEXT_PUBLIC_API_BASE_URL</span> environment variable and restart to change.
          </p>
        </div>
      </Card>
    </div>
  );
}
