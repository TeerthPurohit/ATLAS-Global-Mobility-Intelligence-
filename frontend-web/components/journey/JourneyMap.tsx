"use client";

import { useMemo } from "react";
import Map, { Marker } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { Card } from "@/components/ui/Card";

interface JourneyMapProps {
  pickup: { lat: number; lon: number };
  dropoff: { lat: number; lon: number };
}

// Free OSM raster demo style -- no API key required.
const MAP_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: "raster" as const,
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "&copy; OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster" as const, source: "osm" }],
};

export function JourneyMap({ pickup, dropoff }: JourneyMapProps) {
  const center = useMemo(
    () => ({
      longitude: (pickup.lon + dropoff.lon) / 2,
      latitude: (pickup.lat + dropoff.lat) / 2,
    }),
    [pickup, dropoff]
  );

  return (
    <Card className="overflow-hidden border-2 border-brass/40 p-0 shadow-[0_0_0_1px_rgba(201,146,42,0.15)]">
      <div className="h-80 w-full">
        <Map
          key={`${center.latitude}-${center.longitude}`}
          initialViewState={{ ...center, zoom: 11 }}
          mapStyle={MAP_STYLE}
          style={{ width: "100%", height: "100%" }}
        >
          <Marker longitude={pickup.lon} latitude={pickup.lat} color="#c9922a" />
          <Marker longitude={dropoff.lon} latitude={dropoff.lat} color="#8c4a3c" />
        </Map>
      </div>
    </Card>
  );
}
