// Domain types over the synthetic Sarthi dataset. Field names mirror the CSV
// columns so every figure the agent states is traceable to a source row.

export interface Driver {
  driver_id: string;
  name: string;
  market: string;
  city: string;
  currency: string;
  partner_type: string;
  vehicle: string;
  persona: 'firefighter' | 'grower' | 'stabilizer';
  earnings_tier: string;
  age: number;
  dependents: number;
  religion: string;
  tenure_months: number;
  bank: string;
  ewallet: string;
  rest_dow: string;
  home_lat: number;
  home_lon: number;
  credit_score_band: string;
}

export interface MonthlySummary {
  driver_id: string;
  month: string;
  currency: string;
  gross_income: number;
  platform_fees: number;
  net_income: number;
  total_expense: number;
  essential_expense: number;
  discretionary_expense: number;
  pool_deposits: number;
  pool_withdrawals: number;
  net_pool_savings: number;
  credit_drawn: number;
  net_cashflow: number;
  savings_rate_pct: number;
  expense_to_income_pct: number;
  txn_count: number;
}

export interface Obligation {
  driver_id: string;
  category: string;
  obligation: string;
  frequency: string;
  day_of_month: number;
  typical_amount_low: number;
  typical_amount_high: number;
  currency: string;
  payment_channel: string;
}

export interface CategorySpend {
  driver_id: string;
  month: string;
  category: string;
  total_amount: number;
  txn_count: number;
  avg_amount: number;
  max_amount: number;
}

export interface Goal {
  goal_id: string;
  driver_id: string;
  goal_key: string;
  goal_name: string;
  goal_category: string;
  rationale: string;
  horizon: string;
  priority: number;
  target_amount: number;
  current_amount: number;
  progress_pct: number;
  remaining_amount: number;
  target_date: string;
  days_to_target: number;
  status: string;
  contribution_cadence: string;
  contribution_amount_est: number;
  feasible: boolean;
  on_track: boolean;
  linked_pool_bucket: string;
}

export interface CatalogueGoal {
  goal_key: string;
  goal_name: string;
  category: string;
  horizon: string;
  priority: number;
  rationale: string;
  target_SGD: string;
  who_it_applies_to: string;
}

export interface GoalActionLink {
  goal_id: string;
  driver_id: string;
  goal_name: string;
  iso_week: string;
  weekly_need_sgd: number;
  extra_hours_needed: number;
  week_net_earned_sgd: number;
  week_hours_worked: number;
  notional_available_sgd: number;
  need_covered: boolean;
  gap_sgd: number;
  recommended_windows: string;
}

export interface ZoneCell {
  zone_id: string;
  zone_label: string;
  zone_type: string;
  day_of_week: string;
  hour: number;
  demand_index: number;
  demand_bucket: string;
  surge_multiplier: number;
  weather: string;
  expected_net_per_hour_sgd: number;
  lat: number;
  lon: number;
}

export interface Shift {
  driver_id: string;
  date: string;
  iso_week: string;
  day_of_week: string;
  start_hour: number;
  duration_hours: number;
  zone_id: string;
  zone_label: string;
  trips: number;
  net_earnings_sgd: number;
  net_per_hour_sgd: number;
}

export interface Txn {
  driver_id: string;
  date: string;
  month: string;
  amount: number;
  direction: string;
  category: string;
  subcategory: string;
  merchant_name: string;
  is_essential: boolean;
  is_discretionary: boolean;
  is_internal_movement: boolean;
  is_income: boolean;
  anomaly_flag: string;
  running_balance: number;
  sms_text: string;
}

export interface Dataset {
  drivers: Driver[];
  monthly: MonthlySummary[];
  obligations: Obligation[];
  categories: CategorySpend[];
  goals: Goal[];
  catalogue: CatalogueGoal[];
  goalLinks: GoalActionLink[];
  zones: ZoneCell[];
  shifts: Shift[];
  txns: Txn[];
}

// ---- Agent output contract (Frontend Spec §5.1) ----

export type Tone = 'green' | 'amber' | 'red';
export type Badge =
  | 'On track'
  | 'Ready'
  | 'At risk'
  | 'Protected'
  | 'Tapped';

export interface ReasoningStep {
  step: number;
  text: string;
  tool: string;
  kind: 'plan' | 'tool' | 'guard' | 'compose';
}

export interface DashboardGoal {
  goal_id: string;
  name: string;
  current: number;
  target: number;
  badge: Badge;
  weeklyNeed: number;
  gap: number;
}

export interface DashboardAction {
  id: string;
  primary: boolean;
  text: string;
  buttons: string[];
  link?: string;
}

export interface DashboardState {
  hero: { tone: Tone; icon: string; title: string; body: string };
  runway: {
    days: number;
    comfortLine: number;
    balance: number;
    stressed: boolean;
    dailyBurn: number;
  };
  goals: DashboardGoal[];
  actions: DashboardAction[];
  reasoning: ReasoningStep[];
  allocation: AllocationPlan | null;
  unlocks: Unlock[];
}

export interface AllocationSlice {
  product: 'GXS Bank' | 'GXS Boost Pocket' | 'GXS Invest';
  amount: number;
  icon: string;
  why: string;
}
export interface AllocationPlan {
  surplus: number;
  slices: AllocationSlice[];
}

export interface Unlock {
  key: string;
  title: string;
  detail: string;
  icon: string;
  unlocked: boolean;
  requirement: string;
}
