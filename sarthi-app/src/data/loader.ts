import Papa from 'papaparse';
import type {
  Dataset,
  Driver,
  MonthlySummary,
  Obligation,
  CategorySpend,
  Goal,
  CatalogueGoal,
  GoalActionLink,
  ZoneCell,
  Shift,
  Txn,
} from './types';

const num = (v: unknown): number => {
  const n = parseFloat(String(v ?? '').replace(/,/g, ''));
  return Number.isFinite(n) ? n : 0;
};
const bool = (v: unknown): boolean =>
  String(v ?? '').trim().toLowerCase() === 'true';

async function csv<T>(file: string, map: (r: Record<string, string>) => T): Promise<T[]> {
  const res = await fetch(`${import.meta.env.BASE_URL}data/${file}`);
  if (!res.ok) throw new Error(`Failed to load ${file} (${res.status})`);
  const text = await res.text();
  const parsed = Papa.parse<Record<string, string>>(text, {
    header: true,
    skipEmptyLines: true,
  });
  return parsed.data.filter((r) => r && Object.keys(r).length > 1).map(map);
}

let cache: Dataset | null = null;

export async function loadDataset(): Promise<Dataset> {
  if (cache) return cache;

  const [
    drivers,
    monthly,
    obligations,
    categories,
    goals,
    catalogue,
    goalLinks,
    zones,
    shifts,
    txns,
  ] = await Promise.all([
    csv<Driver>('drivers.csv', (r) => ({
      driver_id: r.driver_id,
      name: r.name,
      market: r.market,
      city: r.city,
      currency: r.currency,
      partner_type: r.partner_type,
      vehicle: r.vehicle,
      persona: r.persona as Driver['persona'],
      earnings_tier: r.earnings_tier,
      age: num(r.age),
      dependents: num(r.dependents),
      religion: r.religion,
      tenure_months: num(r.tenure_months),
      bank: r.bank,
      ewallet: r.ewallet,
      rest_dow: r.rest_dow,
      home_lat: num(r.home_lat),
      home_lon: num(r.home_lon),
      credit_score_band: r.credit_score_band,
    })),
    csv<MonthlySummary>('monthly_summary.csv', (r) => ({
      driver_id: r.driver_id,
      month: r.month,
      currency: r.currency,
      gross_income: num(r.gross_income),
      platform_fees: num(r.platform_fees),
      net_income: num(r.net_income),
      total_expense: num(r.total_expense),
      essential_expense: num(r.essential_expense),
      discretionary_expense: num(r.discretionary_expense),
      pool_deposits: num(r.pool_deposits),
      pool_withdrawals: num(r.pool_withdrawals),
      net_pool_savings: num(r.net_pool_savings),
      credit_drawn: num(r.credit_drawn),
      net_cashflow: num(r.net_cashflow),
      savings_rate_pct: num(r.savings_rate_pct),
      expense_to_income_pct: num(r.expense_to_income_pct),
      txn_count: num(r.txn_count),
    })),
    csv<Obligation>('recurring_obligations.csv', (r) => ({
      driver_id: r.driver_id,
      category: r.category,
      obligation: r.obligation,
      frequency: r.frequency,
      day_of_month: num(r.day_of_month),
      typical_amount_low: num(r.typical_amount_low),
      typical_amount_high: num(r.typical_amount_high),
      currency: r.currency,
      payment_channel: r.payment_channel,
    })),
    csv<CategorySpend>('category_analytics.csv', (r) => ({
      driver_id: r.driver_id,
      month: r.month,
      category: r.category,
      total_amount: num(r.total_amount),
      txn_count: num(r.txn_count),
      avg_amount: num(r.avg_amount),
      max_amount: num(r.max_amount),
    })),
    csv<Goal>('goals.csv', (r) => ({
      goal_id: r.goal_id,
      driver_id: r.driver_id,
      goal_key: r.goal_key,
      goal_name: r.goal_name,
      goal_category: r.goal_category,
      rationale: r.rationale,
      horizon: r.horizon,
      priority: num(r.priority),
      target_amount: num(r.target_amount),
      current_amount: num(r.current_amount),
      progress_pct: num(r.progress_pct),
      remaining_amount: num(r.remaining_amount),
      target_date: r.target_date,
      days_to_target: num(r.days_to_target),
      status: r.status,
      contribution_cadence: r.contribution_cadence,
      contribution_amount_est: num(r.contribution_amount_est),
      feasible: bool(r.feasible),
      on_track: bool(r.on_track),
      linked_pool_bucket: r.linked_pool_bucket,
    })),
    csv<CatalogueGoal>('goal_catalogue.csv', (r) => ({
      goal_key: r.goal_key,
      goal_name: r.goal_name,
      category: r.category,
      horizon: r.horizon,
      priority: num(r.priority),
      rationale: r.rationale,
      target_SGD: r.target_SGD,
      who_it_applies_to: r.who_it_applies_to,
    })),
    csv<GoalActionLink>('goal_action_link.csv', (r) => ({
      goal_id: r.goal_id,
      driver_id: r.driver_id,
      goal_name: r.goal_name,
      iso_week: r.iso_week,
      weekly_need_sgd: num(r.weekly_need_sgd),
      extra_hours_needed: num(r.extra_hours_needed),
      week_net_earned_sgd: num(r.week_net_earned_sgd),
      week_hours_worked: num(r.week_hours_worked),
      notional_available_sgd: num(r.notional_available_sgd),
      need_covered: bool(r.need_covered),
      gap_sgd: num(r.gap_sgd),
      recommended_windows: r.recommended_windows,
    })),
    csv<ZoneCell>('zone_demand_grid.csv', (r) => ({
      zone_id: r.zone_id,
      zone_label: r.zone_label,
      zone_type: r.zone_type,
      day_of_week: r.day_of_week,
      hour: num(r.hour),
      demand_index: num(r.demand_index),
      demand_bucket: r.demand_bucket,
      surge_multiplier: num(r.surge_multiplier),
      weather: r.weather,
      expected_net_per_hour_sgd: num(r.expected_net_per_hour_sgd),
      lat: num(r.lat),
      lon: num(r.lon),
    })),
    csv<Shift>('driver_shift_log.csv', (r) => ({
      driver_id: r.driver_id,
      date: r.date,
      iso_week: r.iso_week,
      day_of_week: r.day_of_week,
      start_hour: num(r.start_hour),
      duration_hours: num(r.duration_hours),
      zone_id: r.zone_id,
      zone_label: r.zone_label,
      trips: num(r.trips),
      net_earnings_sgd: num(r.net_earnings_sgd),
      net_per_hour_sgd: num(r.net_per_hour_sgd),
    })),
    csv<Txn>('transactions.csv', (r) => ({
      driver_id: r.driver_id,
      date: r.date,
      month: r.month,
      amount: num(r.amount),
      direction: r.direction,
      category: r.category,
      subcategory: r.subcategory,
      merchant_name: r.merchant_name,
      is_essential: bool(r.is_essential),
      is_discretionary: bool(r.is_discretionary),
      is_internal_movement: bool(r.is_internal_movement),
      is_income: bool(r.is_income),
      anomaly_flag: r.anomaly_flag,
      running_balance: num(r.running_balance),
      sms_text: r.sms_text,
    })),
  ]);

  cache = {
    drivers,
    monthly,
    obligations,
    categories,
    goals,
    catalogue,
    goalLinks,
    zones,
    shifts,
    txns,
  };
  return cache;
}
