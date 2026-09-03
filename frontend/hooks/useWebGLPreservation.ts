"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import maplibregl from "maplibre-gl";

/**
 * Hook to preserve WebGL context on tab switch / visibility change.
 * Prevents map from losing WebGL context when tab is backgrounded.
 */
export function useWebGLPreservation(mapRef: React.RefObject<maplibregl.Map | null>) {
  const preservationEnabled = useRef(true);
  const wasVisible = useRef(true);

  const handleVisibilityChange = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;

    const isVisible = !document.hidden;

    if (!isVisible && wasVisible.current) {
      // Tab became hidden - try to preserve context
      if (preservationEnabled.current) {
        try {
          map.getCanvas().addEventListener("webglcontextlost", (e) => {
            e.preventDefault();
          });
        } catch {
          // Context preservation not supported
        }
      }
    } else if (isVisible && !wasVisible.current) {
      // Tab became visible again - check if context was lost
      if (map.getCanvas().getContext("webgl") === null) {
        // Context was lost, map will need to reinitialize
        console.warn("WebGL context lost on tab restore, map may need reload");
      }
    }

    wasVisible.current = isVisible;
  }, [mapRef]);

  useEffect(() => {
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [handleVisibilityChange]);

  return {
    enablePreservation: () => { preservationEnabled.current = true; },
    disablePreservation: () => { preservationEnabled.current = false; },
  };
}

/**
 * Hook for lazy-loading map style JSON to improve initial load time.
 * Loads style only when map container is in viewport or about to be shown.
 */
export function useLazyMapStyle(styleUrl: string) {
  const [style, setStyle] = useState<maplibregl.Style | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const loadedRef = useRef(false);

  const loadStyle = useCallback(async () => {
    if (loadedRef.current || loading) return;
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(styleUrl);
      if (!response.ok) throw new Error(`Failed to load map style: ${response.status}`);
      const styleData = await response.json();
      setStyle(styleData);
      loadedRef.current = true;
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error loading map style"));
    } finally {
      setLoading(false);
    }
  }, [styleUrl, loading]);

  return { style, loading, error, loadStyle };
}

/**
 * Hook for reduced motion preference.
 * Returns true if user prefers reduced motion.
 */
export function useReducedMotion() {
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  return reducedMotion;
}