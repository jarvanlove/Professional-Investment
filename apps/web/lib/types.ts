export interface DcaPlan {
  id?: number;
  fund_code: string;
  frequency: "weekly" | "monthly";
  amount: number;
  day_of_week?: number | null;
  day_of_month?: number | null;
  active: boolean;
  note?: string | null;
}

export interface FundDecision {
  code: string;
  name: string;
  score: number;
  score_multiplier: number;
  vol20: number;
  vol_multiplier: number;
  regime_base_weight: number;
  target_weight: number;
  current_value: number;
  target_value: number;
  gap: number;
  action: "BUY" | "SELL" | "HOLD";
  reason_code: string;
  amount: number;
  units: number;
  gates: Record<string, boolean>;
  notes: string[];
  confidence?: number;
  confidence_level?: "high" | "medium" | "low";
  est_fee?: number;
  net_amount?: number;
  avg_fee_rate?: number;
  is_dca?: boolean;
  dca_upcoming?: number;
  base_weight?: number;
}

export interface SignalReport {
  as_of: string;
  regime: string;
  total_value: number;
  portfolio_dd: number;
  peak_profit_rate: number;
  cash_value: number;
  cash_weight: number;
  decisions: FundDecision[];
  weekly_unit_budget: number;
  account_actions: string[];
  weekly_plan?: WeeklyPlan;
}

export interface WeeklyPlan {
  planned_buys: PlannedBuy[];
  planned_sells: PlannedSell[];
  total_buy: number;
  total_sell: number;
  total_est_fee: number;
  total_net_proceeds: number;
  net_cash_change: number;
  dca_schedule: DcaScheduleItem[];
  dca_total: number;
  cash_after: number;
  cash_after_ok: boolean;
  min_cash: number;
  unit_budget_used: number;
  unit_budget_total: number;
  post_trade_weights: Record<string, number>;
  checklist: string[];
}

export interface PlannedBuy {
  code: string;
  name: string;
  amount: number;
  reason_code: string;
  units: number;
  confidence_level?: string;
  dca_upcoming?: number;
}

export interface PlannedSell {
  code: string;
  name: string;
  amount: number;
  reason_code: string;
  est_fee?: number;
  net_amount?: number;
  avg_fee_rate?: number;
  confidence_level?: string;
}

export interface DcaScheduleItem {
  fund_code: string;
  date: string;
  amount: number;
}

export interface Lot {
  buy_date: string;
  shares: number;
  holding_days: number;
  fee_rate: number;
}

export interface PortfolioFund {
  code: string;
  name: string;
  shares: number;
  nav: number | null;
  nav_date: string | null;
  value: number;
  weight: number;
  daily_return: number;
  daily_pnl: number;
  lots: Lot[];
}

export interface AccountInfo {
  cash: number;
  net_contributed: number;
  holdings: Record<string, number>;
  total_value: number;
  peak_value: number;
  portfolio_dd: number;
  peak_profit_rate: number;
}

export interface Portfolio {
  funds: PortfolioFund[];
  account: AccountInfo;
}

export interface Trade {
  id: number;
  date: string;
  direction: "buy" | "sell" | "deposit" | "withdraw";
  fund_code: string | null;
  amount: number;
  shares: number | null;
  nav: number | null;
  reason_code: string | null;
  fee_estimate: number | null;
  note: string | null;
}

export const REGIME_LABELS: Record<string, string> = {
  offensive: "进攻", neutral: "中性", protect: "利润保护", defensive: "防守",
};

export const REASON_LABELS: Record<string, string> = {
  B1: "趋势建仓", B2: "回撤加仓", B3: "突破加仓", B4: "再平衡买入",
  S1: "MA20失效", S2: "MA60失效", S3: "单基金回撤", S4: "组合回撤",
  P1: "过热减仓", P2: "账户利润锁定", N0: "无交易",
};
