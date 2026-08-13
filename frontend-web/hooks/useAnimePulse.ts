"use client";

import { useEffect, useRef } from "react";
import { animate } from "animejs";
import { checkReducedMotion } from "@/lib/motion";

export function useAnimePulse<T extends HTMLElement = HTMLSpanElement>(
  options: { scaleMin?: number; scaleMax?: number; duration?: number; opacityMin?: number } = {}
) {
  const elRef = useRef<T | null>(null);

  useEffect(() => {
    if (!elRef.current) return;
    if (checkReducedMotion()) return;

    const anim = animate(elRef.current, {
      scale: [options.scaleMin ?? 0.85, options.scaleMax ?? 1.3],
      opacity: [options.opacityMin ?? 0.5, 1],
      duration: options.duration ?? 1600,
      ease: "easeInOutSine",
      alternate: true,
      loop: true,
    });

    return () => {
      anim.pause();
    };
  }, [options.scaleMin, options.scaleMax, options.duration, options.opacityMin]);

  return elRef;
}
