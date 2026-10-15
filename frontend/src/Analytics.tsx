import { useEffect, useState } from "react";
import { Download, ChartNoAxesCombined, CircleHelp } from "lucide-react";
import { Empty, PageHeading } from "./App";
import { api } from "./api";
type Row = {
  segment?: string;
  applications: number;
  responses: number;
  minutes: number;
  rate: number | null;
  low: number | null;
  high: number | null;
  responses_per_hour: number | null;
  needed: number;
  additional_to_distinguish?: number | null;
  comparison_note?: string;
};
type Report = {
  overall: Row;
  minimum_sample: number;
  tables: Record<string, Row[]>;
  survival: { day: number; survival: number; low: number; high: number }[];
  survival_note: string;
  suggested_reminder_days: number;
};
const label: Record<string, string> = {
  variant: "Resume variants",
  variant_within_category: "Variants within category",
  category: "Company category",
  size: "Company size",
  platform: "ATS platform",
  seniority: "Seniority",
  remote: "Work style",
  referral: "Referral",
  lead_time: "Time to apply",
};
const percent = (value: number | null) =>
  value === null ? "—" : Math.round(value * 100) + "%";
export default function Analytics({ notify }: { notify: (s: string) => void }) {
  const [data, setData] = useState<Report | null>(null);
  const [dimension, setDimension] = useState("variant");
  useEffect(() => {
    void api<Report>("/analytics")
      .then(setData)
      .catch((e) => notify(String(e)));
  }, []);
  if (!data) return <p>Loading local analytics…</p>;
  return (
    <>
      <PageHeading
        title="Find out what works for you"
        subtitle="Your outcomes, with the uncertainty left in."
      />
      <div className="overview">
        <div>
          <span>
            <strong>{data.overall.applications}</strong>Applications
          </span>
        </div>
        <div>
          <span>
            <strong>{data.overall.responses}</strong>Responses
          </span>
        </div>
        <div>
          <span>
            <strong>{percent(data.overall.rate)}</strong>Response rate
          </span>
        </div>
        <div>
          <span>
            <strong>
              {data.overall.responses_per_hour?.toFixed(1) || "—"}
            </strong>
            Responses per hour
          </span>
        </div>
      </div>
      <p className="info-note">
        <CircleHelp size={13} /> At least {data.minimum_sample} applications per
        segment are needed to show a rate. Differences are observational. They
        may be worth noticing; they do not prove a cause.
      </p>
      {!data.overall.applications ? (
        <Empty
          icon={<ChartNoAxesCombined size={28} />}
          title="Your experience will tell a story"
          text="Log applications and outcomes in Pipeline. Comparisons become useful as your history grows."
        />
      ) : (
        <>
          <div className="button-row">
            <select
              aria-label="Analytics dimension"
              value={dimension}
              onChange={(e) => setDimension(e.target.value)}
            >
              {Object.entries(label).map(([key, value]) => (
                <option key={key} value={key}>
                  {value}
                </option>
              ))}
            </select>
            <a
              className="secondary"
              href={"/api/analytics/export/" + dimension}
            >
              <Download size={14} />
              Export CSV
            </a>
          </div>
          <div className="data-card">
            <table>
              <thead>
                <tr>
                  <th>{label[dimension]}</th>
                  <th>Applications</th>
                  <th>Responses</th>
                  <th>Rate · 95% interval</th>
                  <th>Responses / hour</th>
                </tr>
              </thead>
              <tbody>
                {(data.tables[dimension] || []).map((r) => (
                  <tr key={r.segment}>
                    <td>
                      <strong>{r.segment}</strong>
                    </td>
                    <td>{r.applications}</td>
                    <td>{r.responses}</td>
                    <td
                      title={`${r.comparison_note || ""} ${r.additional_to_distinguish === null ? "No finite comparison estimate at the current gap." : `Approximately ${r.additional_to_distinguish} additional applications per segment needed at the current gap.`}`}
                    >
                      {r.rate === null ? (
                        <span className="muted">
                          {r.needed} more needed · counts only
                        </span>
                      ) : (
                        <>
                          <strong>{percent(r.rate)}</strong>
                          <small>
                            {percent(r.low)}–{percent(r.high)}
                          </small>
                          <div className="rate-track">
                            <i
                              style={{
                                left: (r.low || 0) * 100 + "%",
                                width:
                                  ((r.high || 0) - (r.low || 0)) * 100 + "%",
                              }}
                            />
                            <b style={{ left: r.rate * 100 + "%" }} />
                          </div>
                        </>
                      )}
                    </td>
                    <td>{r.responses_per_hour?.toFixed(2) || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      {data.survival.length > 0 && (
        <section className="settings-form survival-card">
          <h3>Still waiting to hear back</h3>
          <p>{data.survival_note}</p>
          <svg
            viewBox="0 0 650 220"
            role="img"
            aria-label="Kaplan Meier probability of no response"
          >
            <line x1="40" y1="190" x2="625" y2="190" stroke="var(--line)" />
            <line x1="40" y1="20" x2="40" y2="190" stroke="var(--line)" />
            {[0, 0.5, 1].map((v) => (
              <text
                key={v}
                x="4"
                y={190 - v * 170}
                fill="var(--muted)"
                fontSize="10"
              >
                {v * 100}%
              </text>
            ))}
            <path
              fill="none"
              stroke="#789b68"
              strokeWidth="2"
              d={data.survival
                .map(
                  (p, i) =>
                    `${i ? "H" : "M"}${40 + (p.day / (Math.max(...data.survival.map((p) => p.day)) || 1)) * 580}${i ? "V" : ","}${190 - p.survival * 170}`,
                )
                .join(" ")}
            />
            <text x="280" y="215" fontSize="10" fill="var(--muted)">
              Days since applying
            </text>
          </svg>
          <div className="button-row">
            <a className="secondary" href="/api/analytics/export/survival">
              <Download size={14} />
              Export survival table
            </a>
            <button
              className="secondary"
              onClick={() =>
                void api("/settings", "PUT", {
                  reminder_days: data.suggested_reminder_days,
                }).then(() => notify("Follow-up threshold updated"))
              }
            >
              Use {data.suggested_reminder_days}-day follow-up reminder
            </button>
          </div>
        </section>
      )}
    </>
  );
}
