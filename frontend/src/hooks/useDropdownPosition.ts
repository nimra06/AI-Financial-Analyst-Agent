"use client";

import { useCallback, useEffect, useState, type RefObject } from "react";

export type DropdownPosition = {
  top: number;
  right: number;
};

/** Fixed position aligned to anchor's bottom-right (for header dropdowns). */
export function useDropdownPosition(
  anchorRef: RefObject<HTMLElement | null>,
  open: boolean
): DropdownPosition | null {
  const [position, setPosition] = useState<DropdownPosition | null>(null);

  const update = useCallback(() => {
    const el = anchorRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setPosition({
      top: rect.bottom + 8,
      right: Math.max(8, window.innerWidth - rect.right),
    });
  }, [anchorRef]);

  useEffect(() => {
    if (!open) {
      setPosition(null);
      return;
    }
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open, update]);

  return position;
}
