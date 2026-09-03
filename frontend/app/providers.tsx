"use client";

import { useState, useCallback } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // City lists, countries, profiles — effectively static during a session.
        // 10-min stale window means zero re-fetches while navigating around.
        staleTime: 10 * 60_000,
        // Keep in cache for 30 min so back-navigation is instant.
        gcTime: 30 * 60_000,
        refetchOnWindowFocus: false,
        // Don't re-fetch just because the component remounts (route change).
        refetchOnMount: false,
        retry: 1,
        // Serve from cache immediately; revalidate in background only when stale.
        networkMode: "offlineFirst",
      },
    },
  });
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(makeClient);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
