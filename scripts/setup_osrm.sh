#!/usr/bin/env bash
set -euo pipefail

echo "=== Preparing OSRM New York Road Network Map ==="
mkdir -p data/osrm
cd data/osrm

if [ ! -f "new-york-latest.osm.pbf" ]; then
    echo "Downloading OpenStreetMap extract for New York..."
    wget -c https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf
fi

if [ ! -f "new-york-latest.osrm" ]; then
    echo "Extracting road network with OSRM..."
    docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-extract -p /opt/car.lua /data/new-york-latest.osm.pbf
    docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-partition /data/new-york-latest.osrm
    docker run -t -v "${PWD}:/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 osrm-customize /data/new-york-latest.osrm
    echo "OSRM map graph ready!"
else
    echo "OSRM graph already compiled."
fi
