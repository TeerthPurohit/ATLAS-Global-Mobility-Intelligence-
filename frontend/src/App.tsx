import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, useParams, useNavigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MobilityProvider, useMobility } from "./context/MobilityContext";
import { Navbar } from "./components/layout/Navbar";
import { WorldMapView } from "./components/journey/WorldMapView";
import { AnalyzingScreen } from "./components/journey/AnalyzingScreen";
import { ConversationalCityPicker } from "./components/journey/ConversationalCityPicker";
import { CityIntelligenceView } from "./components/city/CityIntelligenceView";
import { Documentation } from "./pages/Documentation";
import { Settings } from "./pages/Settings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5, // 5 minutes
    },
  },
});

// Controller component for /explore/:countryCode
const CountryRouteController: React.FC = () => {
  const { countryCode } = useParams<{ countryCode: string }>();
  const { selectedCountry, selectCountryByCode, isAnalyzing } = useMobility();

  useEffect(() => {
    if (countryCode && (!selectedCountry || selectedCountry.iso_code.toLowerCase() !== countryCode.toLowerCase())) {
      selectCountryByCode(countryCode);
    }
  }, [countryCode, selectedCountry, selectCountryByCode]);

  if (isAnalyzing) {
    return <AnalyzingScreen />;
  }

  return <ConversationalCityPicker />;
};

// Controller component for /explore/:countryCode/:cityId
const CityRouteController: React.FC = () => {
  const { countryCode, cityId } = useParams<{ countryCode: string; cityId: string }>();
  const { selectedCity, selectCityById, selectCountryByCode, selectedCountry } = useMobility();

  useEffect(() => {
    if (countryCode && (!selectedCountry || selectedCountry.iso_code.toLowerCase() !== countryCode.toLowerCase())) {
      selectCountryByCode(countryCode);
    }
    if (cityId && (!selectedCity || selectedCity.id.toLowerCase() !== cityId.toLowerCase())) {
      selectCityById(cityId);
    }
  }, [countryCode, cityId, selectedCountry, selectedCity, selectCountryByCode, selectCityById]);

  return <CityIntelligenceView cityId={cityId || "nyc"} countryCode={countryCode || "us"} />;
};

export const AppContent: React.FC = () => {
  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Navbar onRefresh={() => queryClient.invalidateQueries()} />
      <main className="flex-1 overflow-y-auto bg-slate-950 relative">
        <Routes>
          <Route path="/" element={<WorldMapView />} />
          <Route path="/explore/:countryCode" element={<CountryRouteController />} />
          <Route path="/explore/:countryCode/:cityId" element={<CityRouteController />} />
          <Route path="/docs" element={<Documentation />} />
          <Route path="/settings" element={<Settings />} />
          {/* Fallback to World Map */}
          <Route path="*" element={<WorldMapView />} />
        </Routes>
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <MobilityProvider>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
      </MobilityProvider>
    </QueryClientProvider>
  );
};

export default App;
