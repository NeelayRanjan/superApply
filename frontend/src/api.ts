export type Extract = {
  skills: string[];
  preferred_skills: string[];
  seniority: string;
  years: number;
  remote: string;
  visa: string;
  clearance: boolean;
  geography: string | null;
  degree: string | null;
  compensation: {
    min_cents?: number;
    max_cents?: number;
    currency?: string;
    period?: string;
  };
};
export type Job = {
  id: number;
  title: string;
  company: string;
  company_id: string;
  platform: string;
  tags: string[];
  locations: string[];
  first_seen: string;
  description: string;
  apply_url: string;
  score: number;
  band: string;
  starred: number;
  ghost: number;
  exploration: boolean;
  matched: string[];
  missing: string[];
  dealbreakers: string[];
  extraction: Extract;
  mode: string;
};
export type Company = {
  id: string;
  name: string;
  domain: string;
  platform: string;
  token: string;
  tags: string[];
  verified: boolean;
  notes: string;
  consecutive_failures: number;
  last_success: string | null;
};
export type Profile = {
  titles: string[];
  locations: string[];
  must_skills: string[];
  nice_skills: string[];
  remote: string;
  seniorities: string[];
  dealbreakers: string[];
  compensation_floor_cents: number;
  currency: string;
  needs_sponsorship: boolean;
  has_clearance: boolean;
  strong_threshold: number;
  possible_threshold: number;
  exploration_share: number;
  contact: Record<string, string>;
  explicit_answers: Record<string, string>;
};
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  const response = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: data === undefined ? undefined : JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return response.json();
}
export function salary(job: Job) {
  const c = job.extraction.compensation;
  if (!c.min_cents) return "Not listed";
  const fmt = (n: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: c.currency || "USD",
      notation: n >= 100000 ? "compact" : "standard",
      maximumFractionDigits: 0,
    }).format(n / 100);
  return (
    fmt(c.min_cents) +
    (c.max_cents ? " – " + fmt(c.max_cents) : "") +
    (c.period === "hour" ? "/hr" : "")
  );
}
