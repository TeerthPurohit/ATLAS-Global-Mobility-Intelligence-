import React from "react";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LeafletTooltip } from "react-leaflet";
import { Area, Zone } from "../../api/client";

interface CityAreaMapProps {
  areas: Area[];
  zones?: Zone[];
  selectedArea: Area | null;
  onSelectArea: (area: Area) => void;
  cityCenter: [number, number];
}

// Borough palette for NYC fallback or generic intensity colors
const BOROUGH_COLORS: Record<string, string> = {
  Manhattan: "#f7b733",
  Queens: "#2dd4a7",
  Brooklyn: "#1f9d7c",
  Bronx: "#c9782e",
  "Staten Island": "#e2574c",
  "EWR / Unknown": "#64748b",
};

export const CityAreaMap: React.FC<CityAreaMapProps> = ({
  areas,
  zones = [],
  selectedArea,
  onSelectArea,
  cityCenter,
}) => {
  // Map zone locations if available
  const zoneMap = new Map<number, Zone>();
  zones.forEach((z) => zoneMap.set(z.zone_id, z));

  return (
    <div className="w-full h-full relative bg-slate-950 overflow-hidden">
      <MapContainer
        center={cityCenter}
        zoom={11}
        style={{ width: "100%", height: "100%", background: "#020617" }}
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {areas.map((area) => {
          const matchedZone = zoneMap.get(area.area_id);
          const lat = area.latitude || matchedZone?.latitude || cityCenter[0];
          const lon = area.longitude || matchedZone?.longitude || cityCenter[1];
          const isSelected = selectedArea?.area_id === area.area_id;

          const borough = matchedZone?.borough || "Default";
          const markerColor = BOROUGH_COLORS[borough] || "#2dd4a7";

          return (
            <CircleMarker
              key={area.area_id}
              center={[lat, lon]}
              radius={isSelected ? 10 : 5}
              pathOptions={{
                color: isSelected ? "#ffffff" : markerColor,
                fillColor: markerColor,
                fillOpacity: isSelected ? 1 : 0.75,
                weight: isSelected ? 3 : 1,
              }}
              eventHandlers={{
                click: () => onSelectArea(area),
              }}
            >
              <LeafletTooltip direction="top" offset={[0, -6]} opacity={1}>
                <div className="text-xs font-semibold font-sans">
                  {area.name} <span className="font-mono text-[10px] text-slate-400">(#{area.area_id})</span>
                </div>
              </LeafletTooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
};
