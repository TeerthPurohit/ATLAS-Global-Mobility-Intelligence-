import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

// Register GSAP plugins safely on client side
if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger);
}

export const DURATIONS = {
  instant: 0.1,
  micro: 0.18,
  fast: 0.25,
  standard: 0.4,
  emphasis: 0.6,
  cinematic: 0.9,
} as const;

export const EASINGS = {
  easeOut: "power2.out",
  easeInOut: "power2.inOut",
  expoOut: "expo.out",
  backOut: "back.out(1.4)",
  smooth: "cubic-bezier(0.16, 1, 0.3, 1)",
} as const;

export function checkReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
