"use client";

import { useMemo, useCallback } from "react";
import supercluster from "supercluster";
import type { GeoJSON } from "maplibre-gl";

interface ClusterPoint {
  id: number | string;
  lat: number;
  lng: number;
  properties?: Record<string, unknown>;
}

interface ClusteredPoint extends GeoJSON.Feature<GeoJSON.Point> {
  properties: {
    cluster: boolean;
    cluster_id?: number;
    point_count?: number;
    point_count_abbreviated?: string;
    id?: number | string;
    [key: string]: unknown;
  };
}

/**
 * Hook for clustering markers using supercluster.
 * Useful for city/country level maps with many markers.
 */
export function useMarkerClustering(
  points: ClusterPoint[],
  options: {
    minZoom?: number;
    maxZoom?: number;
    radius?: number;
    extent?: number;
    nodeSize?: number;
    log?: boolean;
  } = {}
) {
  const {
    minZoom = 0,
    maxZoom = 16,
    radius = 40,
    extent = 512,
    nodeSize = 64,
    log = false,
  } = options;

  const clusterIndex = useMemo(() => {
    const index = new supercluster({
      minZoom,
      maxZoom,
      radius,
      extent,
      nodeSize,
      log,
    });

    const geojsonPoints: GeoJSON.Feature<GeoJSON.Point>[] = points.map((point, i) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [point.lng, point.lat],
      },
      properties: {
        id: point.id,
        ...point.properties,
      },
    }));

    index.load(geojsonPoints);
    return index;
  }, [points, minZoom, maxZoom, radius, extent, nodeSize, log]);

  const getClusters = useCallback(
    (bbox: [number, number, number, number], zoom: number): ClusteredPoint[] => {
      return clusterIndex.getClusters(bbox, Math.floor(zoom)) as ClusteredPoint[];
    },
    [clusterIndex]
  );

  const getLeaves = useCallback(
    (clusterId: number, limit = 10, offset = 0): ClusteredPoint[] => {
      return clusterIndex.getLeaves(clusterId, limit, offset) as ClusteredPoint[];
    },
    [clusterIndex]
  );

  const getTile = useCallback(
    (z: number, x: number, y: number) => {
      return clusterIndex.getTile(z, x, y);
    },
    [clusterIndex]
  );

  const getClusterExpansionZoom = useCallback(
    (clusterId: number): number => {
      return clusterIndex.getClusterExpansionZoom(clusterId);
    },
    [clusterIndex]
  );

  return {
    getClusters,
    getLeaves,
    getTile,
    getClusterExpansionZoom,
    clusterIndex,
  };
}

/**
 * Transform clustered points for MapLibre GL source.
 * Expands clusters at zoom level where they should be individual points.
 */
export function expandClusters(
  clusters: ClusteredPoint[],
  getLeaves: (clusterId: number, limit?: number, offset?: number) => ClusteredPoint[],
  zoom: number
): ClusteredPoint[] {
  const expanded: ClusteredPoint[] = [];

  for (const cluster of clusters) {
    if (cluster.properties.cluster) {
      const expansionZoom = cluster.properties.cluster_id
        ? getClusterExpansionZoom(cluster.properties.cluster_id)
        : zoom;

      if (zoom >= expansionZoom) {
        // Expand cluster into individual points
        const leaves = getLeaves(cluster.properties.cluster_id!, 1000);
        expanded.push(...leaves);
      } else {
        // Keep as cluster
        expanded.push(cluster);
      }
    } else {
      // Individual point
      expanded.push(cluster);
    }
  }

  return expanded;
}

/**
 * Get cluster expansion zoom from cluster index.
 * This should be used with a clusterIndex ref.
 */
let clusterIndexRef: supercluster | null = null;

export function setClusterIndexRef(index: supercluster) {
  clusterIndexRef = index;
}

export function getClusterExpansionZoom(clusterId: number): number {
  if (!clusterIndexRef) return 16;
  return clusterIndexRef.getClusterExpansionZoom(clusterId);
}