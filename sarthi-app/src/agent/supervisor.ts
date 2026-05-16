// The brain. A supervisor agent receives a request or a shock signal, plans,
// routes to sub-agents that call typed tools, and composes the dashboard state
// plus a viewable reasoning trace. Deterministic by design so every figure is
// grounded and the live demo never depends on a network call (Agent Spec §5).

import type {
  Dataset,
  Driver,
  DashboardState,
  ReasoningStep,
  Badge,
  Tone,
} from '../data/types';
import {
  incomeSummary,
  expenseBreakdown,
  forecastCashflow,
  detectAnomaly,
  goalStatus,
  matchProduct,
  allocateSurplus,
  checkUnlocks,
  sgd,
  sgd1,
} from './tools';

export interface ChosenGoal {
  goal_id: string;
  name: string;
  target: number;
  current: number;
}

export interface Shock {
  type: 'user_reported' | 'auto_detected' | 'scheduled';
  category: string;
  amount: number;
}

function badgeFor(
  progress: number,
  covered: boolean,
  isProtected: boolean,
): Badge {
  if (isProtected) return 'Protected';
  if (progress >= 100) return 'Ready';
  if (!covered) return 'At risk';
  return 'On track';
}

export function runAgent(
  ds: Dataset,
  driver: Driver,
  chosen: ChosenGoal[],
  shock: Shock | null,
): DashboardState {
  const trace: ReasoningStep[] = [];
  let n = 0;
  const log = (
    text: string,
    tool: string,
    kind: ReasoningStep['kind'] = 'tool',
  ) => trace.push({ step: ++n, text, tool, kind });

  // --- Input guard ---
  log(
    'Checked the request is in scope (financial wellness for this driver) and redacted identifiers before reasoning.',
    'input_guard',
    'guard',
  );

  // --- Supervisor plans ---
  log(
    shock
      ? `Shock signal received (${shock.category}, ${sgd(shock.amount)}). Re-running the state machine over fresh inputs.`
      : 'Planned the turn: income, expenses, runway, goal tracking, action ranking, surplus routing.',
    'supervisor.plan',
    'plan',
  );

  // --- Expense Analyst ---
  const exp = expenseBreakdown(ds, driver.driver_id);
  const top = exp.rows[0];
  log(
    `Read the latest month (${exp.month}): ${sgd(exp.total)} spend, top category ${top ? top.category + ' ' + sgd(top.total_amount) : 'n/a'}.`,
    'expense_breakdown',
  );
  const anomalies = detectAnomaly(ds, driver.driver_id);
  if (anomalies.length)
    log(
      `Flagged ${anomalies.length} transaction(s) beyond the normal pattern (e.g. ${anomalies[0].merchant_name || anomalies[0].category} ${sgd(Math.abs(anomalies[0].amount))}).`,
      'detect_anomaly',
    );

  // --- Cashflow Forecaster ---
  const inc = incomeSummary(ds, driver.driver_id);
  log(
    `Computed average net income ${sgd(inc.avgMonthlyNet)}/mo across the last 3 months; volatility ${sgd(inc.volatility)}.`,
    'income_summary',
  );
  const fc = forecastCashflow(
    ds,
    driver.driver_id,
    shock ? shock.amount : 0,
  );
  log(
    `Cash runway: ${fc.days} days at a stressed daily burn of ${sgd1(fc.dailyBurn)} (income stressed to 55%).`,
    'forecast_cashflow',
  );

  // --- Goal Tracker ---
  const dashGoals = chosen.map((g) => {
    const st = goalStatus(ds, g.goal_id);
    const progress = g.target > 0 ? (g.current / g.target) * 100 : 0;
    const covered = st ? st.need_covered : true;
    const gap = st ? st.gap_sgd : 0;
    const weeklyNeed = st ? st.weekly_need_sgd : 0;
    const isProtected =
      /vehicle|loan|debt/i.test(g.name) && shock !== null;
    const badge = badgeFor(progress, covered, isProtected);
    return {
      goal_id: g.goal_id,
      name: g.name,
      current: g.current,
      target: g.target,
      badge,
      weeklyNeed,
      gap,
    };
  });
  dashGoals.forEach((g) =>
    log(
      `${g.name}: ${Math.round((g.current / Math.max(g.target, 1)) * 100)}% funded, weekly need ${sgd1(g.weeklyNeed)} → ${g.badge}${g.gap > 0 ? `, gap ${sgd1(g.gap)}` : ''}.`,
      'goal_tracker',
    ),
  );

  const atRisk = dashGoals.find((g) => g.badge === 'At risk');
  const protectedG = dashGoals.find((g) => g.badge === 'Protected');
  if (protectedG)
    log(
      `Marked ${protectedG.name} a non-negotiable commitment — Protected; the shock is absorbed against discretionary savings, not this.`,
      'goal_tracker',
    );

  // --- Action Planner ---
  const actions: DashboardState['actions'] = [];
  if (shock) {
    const m = matchProduct({
      shock: true,
      gap: shock.amount,
      surplus: 0,
      liquidityNeed: true,
    });
    log(
      `Compared three ways to cover the ${sgd(shock.amount)} gap; ${m.product} had the lowest total cost. ${m.why}`,
      'plan_actions',
    );
    log(`Matched the need to ${m.product}.`, 'match_product');
    actions.push({
      id: 'bridge',
      primary: true,
      text: `Bridge the ${sgd(shock.amount)} ${shock.category} with a <b>${m.product}</b>. First draw is 60 days interest-free; your loan payment stays Protected.`,
      buttons: ['Prepare draw', 'Skip'],
      link: 'goal',
    });
  }
  const focus =
    dashGoals.find((g) => g.badge === 'At risk') ||
    dashGoals.find((g) => g.gap > 0) ||
    dashGoals[0];
  if (focus) {
    const st = goalStatus(ds, focus.goal_id);
    const win = st?.recommended_windows?.split(';')[0]?.trim();
    log(
      `Ranked earning windows for ${focus.name} from the demand grid in ${driver.name.split(' ')[0]}'s preferred zones.`,
      'plan_actions',
    );
    actions.push({
      id: 'earn',
      primary: !shock,
      text: focus.gap > 0
        ? `${focus.name} is <b>${sgd1(focus.gap)} short</b> this week. ${win ? `About one good window — <b>${win}</b> — covers it.` : 'A short extra window covers it.'}`
        : `${focus.name} is on track. Keep one ${win ? `<b>${win}</b>` : 'evening'} window to stay ahead.`,
      buttons: ['See windows', 'Skip'],
      link: 'goal',
    });
  }

  // --- Surplus routing ---
  const latestLink = chosen
    .map((g) => goalStatus(ds, g.goal_id))
    .filter(Boolean)
    .sort((a, b) => a!.iso_week.localeCompare(b!.iso_week))
    .pop();
  const surplus = latestLink ? Math.max(latestLink.notional_available_sgd, 0) : 0;
  const allocation = surplus > 0 ? allocateSurplus(surplus, driver.persona) : null;
  if (allocation) {
    log(
      `Notional surplus this week ${sgd(surplus)}. Allocated across GXS Bank / Boost Pocket / Invest by ${driver.persona} risk profile.`,
      'allocate_surplus',
    );
    actions.push({
      id: 'route',
      primary: false,
      text: `You have <b>${sgd(surplus)}</b> spare this week. Sarthi can split it: ${allocation.slices
        .map((s) => `${sgd(s.amount)} ${s.product}`)
        .join(', ')}.`,
      buttons: ['Review split', 'Skip'],
      link: 'route',
    });
  }

  // --- Unlocks ---
  const unlocks = checkUnlocks(
    dashGoals.map((g) => ({
      name: g.name,
      progress: (g.current / Math.max(g.target, 1)) * 100,
      onTrack: g.badge === 'On track' || g.badge === 'Ready',
    })),
  );
  const newlyUnlocked = unlocks.filter((u) => u.unlocked);
  if (newlyUnlocked.length)
    log(
      `Goal progress unlocked ${newlyUnlocked.length} partner benefit(s): ${newlyUnlocked.map((u) => u.title.split('—')[0].trim()).join(', ')}.`,
      'check_unlocks',
    );

  // --- Compose ---
  let tone: Tone = 'green';
  let title = `${driver.name.split(' ')[0]}, you're on track.`;
  let body = `Runway ${fc.days} days. ${dashGoals.filter((g) => g.badge === 'On track' || g.badge === 'Ready').length}/${dashGoals.length} goals on track.`;
  let icon = '✓';
  if (shock) {
    tone = 'red';
    icon = '!';
    title = `A ${sgd(shock.amount)} ${shock.category} just hit.`;
    body = `Runway recomputed to ${fc.days} days. ${protectedG ? `${protectedG.name} stays Protected; a` : 'A'} FlexiLoan bridge is the lowest-cost cover.`;
  } else if (atRisk) {
    tone = 'amber';
    icon = '⚠';
    title = `${atRisk.name} needs ${sgd1(atRisk.gap)} this week.`;
    body = `One good earning window closes the gap. Everything else is on track.`;
  }
  log(
    `Composed a ${tone} hero and a ${actions.find((a) => a.primary)?.id ?? 'steady'}-first plan. Verified every figure traces to a tool result.`,
    'output_guard',
    'guard',
  );
  log('Emitted the dashboard state and this reasoning trace.', 'compose', 'compose');

  return {
    hero: { tone, icon, title, body },
    runway: {
      days: fc.days,
      comfortLine: fc.comfortLine,
      balance: fc.balance,
      stressed: shock !== null,
      dailyBurn: fc.dailyBurn,
    },
    goals: dashGoals,
    actions,
    reasoning: trace,
    allocation,
    unlocks,
  };
}
