"use client";

import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { checkReducedMotion } from "@/lib/motion";

interface NumberTickerProps {
  value: number;
  direction?: "up" | "down";
  delay?: number;
  duration?: number;
  className?: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

export function NumberTicker({
  value,
  delay = 0,
  duration = 1.2,
  className = "",
  prefix = "",
  suffix = "",
  decimals = 0,
}: NumberTickerProps) {
  const nodeRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    const node = nodeRef.current;
    if (!node) return;

    if (checkReducedMotion()) {
      node.textContent = `${prefix}${value.toFixed(decimals)}${suffix}`;
      return;
    }

    const obj = { val: 0 };
    const ctx = gsap.context(() => {
      gsap.to(obj, {
        val: value,
        duration,
        delay,
        ease: "power2.out",
        onUpdate: () => {
          if (node) {
            node.textContent = `${prefix}${obj.val.toLocaleString(undefined, {
              minimumFractionDigits: decimals,
              maximumFractionDigits: decimals,
            })}${suffix}`;
          }
        },
      });
    });

    return () => ctx.revert();
  }, [value, delay, duration, prefix, suffix, decimals]);

  return <span ref={nodeRef} className={className}>{prefix}{value.toFixed(decimals)}{suffix}</span>;
}
