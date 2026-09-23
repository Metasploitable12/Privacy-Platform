"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "../apiClient";

type ProcessingActivity = {
  id: string;
  name: string;
  status: string;
  version: number;
  business_function: string | null;
};

export default function RopaListPage() {
  const [activities, setActivities] = useState<ProcessingActivity[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ProcessingActivity[]>("/ropa")
      .then(setActivities)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <h1>Processing Activities (ROPA)</h1>
      {error && <p style={{ color: "#b91c1c" }}>{error}</p>}
      {!error && !activities && <p>Loading…</p>}
      {activities && (
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#fff" }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #e2e4e8" }}>
              <th style={{ padding: 8 }}>Name</th>
              <th style={{ padding: 8 }}>Status</th>
              <th style={{ padding: 8 }}>Version</th>
              <th style={{ padding: 8 }}>Business Function</th>
            </tr>
          </thead>
          <tbody>
            {activities.map((a) => (
              <tr key={a.id} style={{ borderBottom: "1px solid #f1f2f4" }}>
                <td style={{ padding: 8 }}>{a.name}</td>
                <td style={{ padding: 8 }}>{a.status}</td>
                <td style={{ padding: 8 }}>{a.version}</td>
                <td style={{ padding: 8 }}>{a.business_function ?? "—"}</td>
              </tr>
            ))}
            {activities.length === 0 && (
              <tr>
                <td colSpan={4} style={{ padding: 8, color: "#6b7280" }}>
                  No processing activities yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
