"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { JourneyForm } from "@/components/journey/JourneyForm";
import { JourneyMap } from "@/components/journey/JourneyMap";
import { JourneyResults } from "@/components/journey/JourneyResults";
import { type JourneyRequest } from "@/lib/api";
import { useGsapEntrance } from "@/hooks/useGsapEntrance";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin } from "lucide-react";

const defaultPickup = { lat: 40.7484, lon: -73.9857 };
const defaultDropoff = { lat: 40.7061, lon: -74.0088 };

export default function JourneyPage() {
  return (
    <Suspense fallback={null}>
      <JourneyPageContent />
    </Suspense>
  );
}

function JourneyPageContent() {
  const containerRef = useGsapEntrance(".gsap-reveal", { stagger: 0.1, yOffset: 16 });
  const [route, setRoute] = useState({ pickup: defaultPickup, dropoff: defaultDropoff });
  const [journeyRequest, setJourneyRequest] = useState<JourneyRequest | null>(null);

  function handleSubmit(req: JourneyRequest) {
    setRoute({
      pickup: { lat: req.pickup_lat, lon: req.pickup_lon },
      dropoff: { lat: req.dropoff_lat, lon: req.dropoff_lon },
    });
    setJourneyRequest(req);
  }

  const showResults = !!journeyRequest;

  return (
    <div ref={containerRef} className="flex flex-col gap-12">
      {/* Header */}
      <section className="gsap-reveal flex flex-col gap-3">
        <span className="font-label-sm text-brass tracking-wider">
          Real-Time Intelligence
        </span>
        <h1 className="font-display-lg text-ink-primary">
          Journey Analysis
        </h1>
        <p className="font-body-md max-w-2xl text-ink-secondary">
          Select pickup and dropoff points to calculate fare, ETA, demand, and risk intelligence in real-time.
        </p>
      </section>

      {/* Main Layout */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[420px_1fr]">
        {/* Sidebar Form */}
        <div className="gsap-reveal flex flex-col gap-6">
          <JourneyForm onSubmit={handleSubmit} isPending={false} />
          <div className="border border-surface-border bg-surface-1 p-6 rounded-sm">
            <JourneyMap pickup={route.pickup} dropoff={route.dropoff} />
          </div>
        </div>

        {/* Results Area */}
        <div className="gsap-reveal">
          <AnimatePresence mode="wait">
            {showResults && journeyRequest ? (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              >
                <JourneyResults request={journeyRequest} />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex h-full min-h-[500px] items-center justify-center border border-surface-border bg-surface-1 p-12 text-center rounded-sm"
              >
                <div className="max-w-md space-y-4">
                  <div className="flex justify-center">
                    <div className="p-3 bg-brass/10 rounded-sm">
                      <MapPin className="h-6 w-6 text-brass" />
                    </div>
                  </div>
                  <h3 className="font-section-lg text-ink-primary">
                    Configure Your Route
                  </h3>
                  <p className="font-body-sm text-ink-secondary">
                    Enter pickup and dropoff coordinates to receive real-time fare estimates, ETA predictions, demand analysis, and risk assessment.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
