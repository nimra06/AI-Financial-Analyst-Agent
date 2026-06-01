"use client";

import { AlertTriangle } from "lucide-react";

export function DisclaimerBanner() {
  return (
    <div className="flex items-center gap-2 border-b border-warning/20 bg-warning/10 px-6 py-2 text-xs text-warning lg:px-8">
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
      <p>
        <span className="font-medium">Demo environment</span> — for analysis only, not
        financial, tax, or investment advice. Verify all figures against your source systems.
      </p>
    </div>
  );
}
