"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { checkReducedMotion, EASINGS } from "@/lib/motion";

interface EntranceOptions {
  stagger?: number;
  delay?: number;
  duration?: number;
  yOffset?: number;
}

export function useGsapEntrance(selector = ".gsap-reveal", options: EntranceOptions = {}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    if (checkReducedMotion()) return;

    const elements = containerRef.current.querySelectorAll(selector);
    if (!elements || elements.length === 0) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        elements,
        {
          opacity: 0,
          y: options.yOffset ?? 18,
        },
        {
          opacity: 1,
          y: 0,
          duration: options.duration ?? 0.55,
          delay: options.delay ?? 0.05,
          stagger: options.stagger ?? 0.07,
          ease: EASINGS.easeOut,
          clearProps: "transform,opacity",
        }
      );
    }, containerRef);

    return () => ctx.revert();
  }, [selector, options.stagger, options.delay, options.duration, options.yOffset]);

  return containerRef;
}
