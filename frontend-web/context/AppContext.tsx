"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import type { City, Country, JourneyRequest, VehicleClass } from "@/lib/api";

interface AppContextValue {
  // Drill-down state
  selectedCountry: Country | null;
  setSelectedCountry: (country: Country | null) => void;
  selectedCity: City | null;
  setSelectedCity: (city: City | null) => void;
  selectedArea: { id: string; name: string } | null;
  setSelectedArea: (area: { id: string; name: string } | null) => void;

  // Shared journey request
  journeyRequest: JourneyRequest | null;
  setJourneyRequest: (req: JourneyRequest | null) => void;

  // UI preferences
  theme: "dark" | "light";
  setTheme: (theme: "dark" | "light") => void;
  mapStyle: "dark" | "satellite" | "light";
  setMapStyle: (style: "dark" | "satellite" | "light") => void;

  // Toast notifications
  toast: { message: string; type: "info" | "success" | "warning" | "error" } | null;
  showToast: (message: string, type?: "info" | "success" | "warning" | "error") => void;

  // Recent items (localStorage backed)
  recentCities: City[];
  addRecentCity: (city: City) => void;
  recentJourneys: JourneyRequest[];
  addRecentJourney: (journey: JourneyRequest) => void;

  // Analyst session
  analystSessionId: string | null;
  setAnalystSessionId: (id: string | null) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [selectedArea, setSelectedArea] = useState<{ id: string; name: string } | null>(null);
  const [journeyRequest, setJourneyRequest] = useState<JourneyRequest | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [mapStyle, setMapStyle] = useState<"dark" | "satellite" | "light">("dark");
  const [toast, setToast] = useState<AppContextValue["toast"]>(null);
  const [recentCities, setRecentCities] = useState<City[]>([]);
  const [recentJourneys, setRecentJourneys] = useState<JourneyRequest[]>([]);
  const [analystSessionId, setAnalystSessionId] = useState<string | null>(null);

  const showToast = useCallback((message: string, type: "info" | "success" | "warning" | "error" = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  const addRecentCity = useCallback((city: City) => {
    setRecentCities((prev) => {
      const filtered = prev.filter((c) => c.id !== city.id);
      return [city, ...filtered].slice(0, 5);
    });
  }, []);

  const addRecentJourney = useCallback((journey: JourneyRequest) => {
    setRecentJourneys((prev) => {
      const key = `${journey.pickup_lat},${journey.pickup_lon}-${journey.dropoff_lat},${journey.dropoff_lon}`;
      const filtered = prev.filter((j) => `${j.pickup_lat},${j.pickup_lon}-${j.dropoff_lat},${j.dropoff_lon}` !== key);
      return [journey, ...filtered].slice(0, 10);
    });
  }, []);

  return (
    <AppContext.Provider
      value={{
        selectedCountry,
        setSelectedCountry,
        selectedCity,
        setSelectedCity,
        selectedArea,
        setSelectedArea,
        journeyRequest,
        setJourneyRequest,
        theme,
        setTheme,
        mapStyle,
        setMapStyle,
        toast,
        showToast,
        recentCities,
        addRecentCity,
        recentJourneys,
        addRecentJourney,
        analystSessionId,
        setAnalystSessionId,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}