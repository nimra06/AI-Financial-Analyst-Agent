"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { WhyInsight } from "@/types/dashboard";

export function WhyPanel({ insights }: { insights: WhyInsight[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Explainability</CardTitle>
        <CardDescription>How each metric was calculated</CardDescription>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-text-secondary">
              <th className="pb-2 pr-3 font-medium">Metric</th>
              <th className="pb-2 pr-3 font-medium">Value</th>
              <th className="pb-2 pr-3 font-medium">Period</th>
              <th className="pb-2 font-medium">Formula</th>
            </tr>
          </thead>
          <tbody>
            {insights.map((row, i) => (
              <tr key={i} className="border-b border-white/5">
                <td className="py-2 pr-3">
                  {row.metric}{" "}
                  <Badge variant="muted" className="ml-1">
                    {row.category}
                  </Badge>
                </td>
                <td className="py-2 pr-3">{row.value}</td>
                <td className="py-2 pr-3 text-text-secondary">{row.period}</td>
                <td className="py-2 text-text-secondary">{row.formula_hint}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
