import React, { createContext, useContext, useState, useEffect } from "react";
import {
  Country,
  City,
  Area,
  CityProfileResponse,
  CityContextResponse,
  GeographyCountry,
  fetchCountries,
  fetchCountryCities,
  fetchCityProfile,
  fetchCityContext,
  fetchGeographyCountries,
} from "../api/client";

export type CityIntelligenceState =
  | "OBSERVED_MOBILITY"
  | "MODELED_MOBILITY"
  | "CONTEXT_AVAILABLE"
  | "GEOGRAPHIC_ONLY"
  | "UNAVAILABLE"
  | "LOADING"
  | "ERROR";

interface MobilityContextType {
  selectedCountry: Country | null;
  selectedCity: City | null;
  selectedArea: Area | null;
  selectedMetric: string;
  isAnalyzing: boolean;
  activeDrawer: "chat" | "data" | "methodology" | "settings" | "search" | null;
  
  selectedCityProfile: CityProfileResponse | null;
  selectedCityContext: CityContextResponse | null;
  cityIntelligenceState: CityIntelligenceState;
  
  allCountries: Country[];
  countryCities: City[];
  geographyCountries: GeographyCountry[];
  loadingCountries: boolean;
  
  setSelectedCountry: (country: Country | null) => void;
  setSelectedCity: (city: City | null) => void;
  setSelectedArea: (area: Area | null) => void;
  setSelectedMetric: (metric: string) => void;
  setIsAnalyzing: (analyzing: boolean) => void;
  setActiveDrawer: (drawer: "chat" | "data" | "methodology" | "settings" | "search" | null) => void;
  
  selectCountryByCode: (code: string) => Promise<Country | null>;
  selectCityById: (cityId: string) => Promise<City | null>;
  selectGlobalCity: (cityId: string) => Promise<CityProfileResponse | null>;
  resetToWorld: () => void;
  resetToCountry: () => void;
}

const MobilityContext = createContext<MobilityContextType | undefined>(undefined);

export const MobilityProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [selectedCity, setSelectedCity] = useState<City | null>(null);
  const [selectedArea, setSelectedArea] = useState<Area | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>("demand");
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [activeDrawer, setActiveDrawer] = useState<"chat" | "data" | "methodology" | "settings" | "search" | null>(null);
  
  const [selectedCityProfile, setSelectedCityProfile] = useState<CityProfileResponse | null>(null);
  const [selectedCityContext, setSelectedCityContext] = useState<CityContextResponse | null>(null);
  const [cityIntelligenceState, setCityIntelligenceState] = useState<CityIntelligenceState>("GEOGRAPHIC_ONLY");

  const [allCountries, setAllCountries] = useState<Country[]>([]);
  const [countryCities, setCountryCities] = useState<City[]>([]);
  const [geographyCountries, setGeographyCountries] = useState<GeographyCountry[]>([]);
  const [loadingCountries, setLoadingCountries] = useState<boolean>(true);

  // Load backend countries and geography countries on mount
  useEffect(() => {
    Promise.all([
      fetchCountries().catch(() => []),
      fetchGeographyCountries().catch(() => []),
    ]).then(([countries, geoCountries]) => {
      setAllCountries(countries);
      setGeographyCountries(geoCountries);
      setLoadingCountries(false);
    });
  }, []);

  // When selectedCountry changes, load its cities
  useEffect(() => {
    if (selectedCountry && selectedCountry.supported) {
      fetchCountryCities(selectedCountry.iso_code)
        .then((cities) => {
          setCountryCities(cities);
        })
        .catch((err) => {
          console.error(`Failed to fetch cities for ${selectedCountry.iso_code}:`, err);
          setCountryCities([]);
        });
    } else {
      setCountryCities([]);
    }
  }, [selectedCountry]);

  const selectCountryByCode = async (code: string): Promise<Country | null> => {
    let country = allCountries.find((c) => c.iso_code.toUpperCase() === code.toUpperCase());
    if (!country && allCountries.length === 0) {
      try {
        const freshCountries = await fetchCountries();
        setAllCountries(freshCountries);
        country = freshCountries.find((c) => c.iso_code.toUpperCase() === code.toUpperCase());
      } catch (e) {
        console.error(e);
      }
    }
    if (country) {
      setSelectedCountry(country);
      setSelectedCity(null);
      setSelectedArea(null);
      return country;
    }
    return null;
  };

  const selectCityById = async (cityId: string): Promise<City | null> => {
    let city = countryCities.find((c) => c.id.toLowerCase() === cityId.toLowerCase());
    if (city) {
      setSelectedCity(city);
      setSelectedArea(null);
      selectGlobalCity(cityId);
      return city;
    }
    // Even if not in seeded countryCities array, resolve profile via global city engine
    selectGlobalCity(cityId);
    return null;
  };

  const selectGlobalCity = async (cityId: string): Promise<CityProfileResponse | null> => {
    setCityIntelligenceState("LOADING");
    try {
      const profile = await fetchCityProfile(cityId);
      setSelectedCityProfile(profile);

      // Derive intelligence state dynamically from backend capabilities
      if (profile.capabilities.observed_mobility) {
        setCityIntelligenceState("OBSERVED_MOBILITY");
      } else if (profile.capabilities.cross_city_model) {
        setCityIntelligenceState("MODELED_MOBILITY");
      } else if (profile.capabilities.context) {
        setCityIntelligenceState("CONTEXT_AVAILABLE");
      } else {
        setCityIntelligenceState("GEOGRAPHIC_ONLY");
      }

      // Load context asynchronously
      fetchCityContext(cityId)
        .then((ctx) => setSelectedCityContext(ctx))
        .catch((err) => {
          console.warn(`Context not available for ${cityId}:`, err);
          setSelectedCityContext(null);
        });

      return profile;
    } catch (err) {
      console.error(`Failed to resolve city profile for ${cityId}:`, err);
      setCityIntelligenceState("UNAVAILABLE");
      setSelectedCityProfile(null);
      setSelectedCityContext(null);
      return null;
    }
  };

  const resetToWorld = () => {
    setSelectedCountry(null);
    setSelectedCity(null);
    setSelectedArea(null);
    setSelectedCityProfile(null);
    setSelectedCityContext(null);
    setIsAnalyzing(false);
  };

  const resetToCountry = () => {
    setSelectedCity(null);
    setSelectedArea(null);
    setSelectedCityProfile(null);
    setSelectedCityContext(null);
    setIsAnalyzing(false);
  };

  return (
    <MobilityContext.Provider
      value={{
        selectedCountry,
        selectedCity,
        selectedArea,
        selectedMetric,
        isAnalyzing,
        activeDrawer,
        selectedCityProfile,
        selectedCityContext,
        cityIntelligenceState,
        allCountries,
        countryCities,
        geographyCountries,
        loadingCountries,
        setSelectedCountry,
        setSelectedCity,
        setSelectedArea,
        setSelectedMetric,
        setIsAnalyzing,
        setActiveDrawer,
        selectCountryByCode,
        selectCityById,
        selectGlobalCity,
        resetToWorld,
        resetToCountry,
      }}
    >
      {children}
    </MobilityContext.Provider>
  );
};

export const useMobility = (): MobilityContextType => {
  const context = useContext(MobilityContext);
  if (!context) {
    throw new Error("useMobility must be used within a MobilityProvider");
  }
  return context;
};
