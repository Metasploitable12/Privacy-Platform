"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "./apiClient";

type DashboardMetrics = {
  total_processing_activities: number;
  draft_count: number;
  in_review_count: number;
  approved_count: number;
  retired_count: number;
  approved_percentage: number;
};

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DashboardMetrics>("/dashboard/metrics")
      .then(setMetrics)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <p style={{ color: "#b91c1c" }}>
        Could not load dashboard metrics: {error}. Make sure you are
        authenticated (see /api/v1/auth/oidc/callback) and the backend is
        running.
      </p>
    );
  }

  if (!metrics) return <p>Loading…</p>;

  const cards: { label: string; value: number | string }[] = [
    { label: "Total Processing Activities", value: metrics.total_processing_activities },
    { label: "Draft", value: metrics.draft_count },
    { label: "In Review", value: metrics.in_review_count },
    { label: "Approved", value: metrics.approved_count },
    { label: "Retired", value: metrics.retired_count },
    { label: "Approved %", value: `${metrics.approved_percentage}%` },
  ];

  return (
    <div>
      <h1>Privacy Health</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        {cards.map((c) => (
          <div key={c.label} style={{ background: "#fff", border: "1px solid #e2e4e8", borderRadius: 8, padding: 16 }}>
            <div style={{ fontSize: 13, color: "#6b7280" }}>{c.label}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
