export interface MonthlyPoint {
  month: string;
  revenue: number;
  gross_profit: number;
  net_profit: number;
  opex: number;
  gross_margin_pct: number;
  opex_ratio_pct: number;
}

export interface Kpis {
  latest_month: string;
  latest_revenue: number;
  latest_net_profit: number;
  latest_gross_margin_pct: number;
  latest_opex_ratio_pct: number;
  mom_revenue_growth_pct: number | null;
  mom_profit_growth_pct: number | null;
  avg_revenue_3m: number;
  avg_profit_3m: number;
  total_revenue: number;
  best_month_by_revenue: string;
  top_expense_categories: { category: string; amount: number }[];
  monthly_records: Record<string, unknown>[];
}

export interface AnomalyFlag {
  month: string;
  metric: string;
  value: number;
  method: string;
  severity: string;
  description: string;
}

export interface DashboardData {
  session_id: string;
  source_file: string;
  period_count: number;
  kpis: Kpis;
  snapshot: Record<string, unknown>;
  monthly_records: Record<string, unknown>[];
  chart_series: MonthlyPoint[];
  top_expense_categories: { category: string; amount: number }[];
  raw_preview: Record<string, unknown>[];
  anomalies: {
    flags: AnomalyFlag[];
    summary: Record<string, number>;
    warnings?: string[];
  };
  warnings: string[];
  industry?: string;
  budget_variance?: BudgetVariance;
  benchmarks?: BenchmarkResult;
}

export interface SessionMeta {
  session_id: string;
  source_file: string;
  period_count: number;
  latest_month: string;
  created_at: string;
}

export interface ExecutiveSummary {
  summary: string;
  trends: string[];
  risks: string[];
  opportunities: string[];
  recommendations: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
}

export interface ForecastPayload {
  metric: string;
  horizon_months: number;
  history: { month: string; value: number; lower: number; upper: number }[];
  forecast: { month: string; value: number; lower: number; upper: number }[];
  summary: Record<string, number | string | null>;
  warnings: string[];
}

export interface WhyInsight {
  metric: string;
  value: string;
  period: string;
  formula_hint: string;
  category: string;
}

export interface FreelanceClientRow {
  client: string;
  amount: number;
  share_pct: number;
}

export interface UploadValidation {
  errors: string[];
  warnings: string[];
  row_count: number;
  detected_format?: string | null;
  freelance_insights?: string[];
  freelance_summary?: {
    insights?: string[];
    clients?: FreelanceClientRow[];
    total_lifetime?: number;
    client_count?: number;
    top_clients?: FreelanceClientRow[];
  } | null;
}

export interface ReportPayload {
  html: string;
  markdown: string;
  pdf_available: boolean;
  pdf_base64?: string | null;
  warnings: string[];
}

export interface AuditEvent {
  id: number;
  event_type: string;
  actor: string;
  session_id?: string | null;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface RetentionPolicy {
  retention_days: number;
  expiring_soon: { session_id: string; source_file: string; created_at: string }[];
  last_purge_count: number;
}

export interface BudgetVarianceLine {
  metric: string;
  actual: number;
  budget: number;
  variance: number;
  variance_pct: number | null;
  favorable: boolean;
}

export interface BudgetVariance {
  available: boolean;
  reason?: string;
  latest_month?: string;
  lines?: BudgetVarianceLine[];
}

export interface BenchmarkScore {
  metric: string;
  value: number;
  benchmark_low: number;
  benchmark_mid: number;
  benchmark_high: number;
  status: string;
  vs_typical: number;
}

export interface BenchmarkResult {
  industry: string;
  scores: BenchmarkScore[];
  disclaimer?: string;
}

export interface CompareResult {
  session_a: { session_id: string; source_file: string; period_count: number; latest_month?: string };
  session_b: { session_id: string; source_file: string; period_count: number; latest_month?: string };
  deltas: { metric: string; session_a: number; session_b: number; delta: number; delta_pct: number | null }[];
  summary: Record<string, unknown>;
}

export interface ScenarioImpact {
  metric: string;
  baseline: number;
  projected: number;
  delta: number;
  delta_pct: number | null;
}

export interface ScenarioResult {
  latest_month: string;
  impact: ScenarioImpact[];
  assumptions: Record<string, unknown>;
}

export interface AlertItem {
  id: number;
  session_id: string;
  rule_id: string;
  severity: string;
  title: string;
  message: string;
  read_at?: string | null;
  created_at: string;
}

export interface ScheduledReport {
  id: number;
  session_id: string;
  label: string;
  cadence: string;
  format: string;
  recipients: string[];
  enabled: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
}
