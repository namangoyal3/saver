// Ask Sarthi — grounded, deterministic Q&A. Answers come from the same typed
// tools as the dashboard. Out-of-scope questions (tax, legal, investment
// advice) are refused with a pointer to a qualified source (Agent Spec §7).

import type { Dataset, Driver, DashboardState } from '../data/types';
import { incomeSummary, expenseBreakdown, cpfProject, sgd, sgd1 } from './tools';

export interface Answer {
  text: string;
  source: string;
}

const OUT_OF_SCOPE =
  /\b(tax|legal|lawyer|stock pick|which stock|crypto|bitcoin|guarantee|advice on shares)\b/i;

export function answer(
  q: string,
  ds: Dataset,
  driver: Driver,
  state: DashboardState,
): Answer {
  const t = q.toLowerCase();

  if (OUT_OF_SCOPE.test(t))
    return {
      text: 'That is tax / legal / investment-advice territory — outside what I should answer. Please speak to a licensed adviser or IRAS / MAS for that. I can help with your cashflow, goals and earning plan.',
      source: 'input_guard',
    };

  if (/runway|how long|okay|buffer|last/.test(t))
    return {
      text: `Your cash runway is ${state.runway.days} days. That is balance minus a one-month comfort line (${sgd(state.runway.comfortLine)}), divided by a stressed daily burn of ${sgd1(state.runway.dailyBurn)} — i.e. assuming work slows to 55%.`,
      source: 'forecast_cashflow',
    };

  if (/income|earn|make|net/.test(t)) {
    const inc = incomeSummary(ds, driver.driver_id);
    return {
      text: `Your average net income is ${sgd(inc.avgMonthlyNet)}/month over the last 3 months, swinging about ${sgd(inc.volatility)} between months.`,
      source: 'income_summary',
    };
  }

  if (/spend|expense|cost|where.*money|category/.test(t)) {
    const e = expenseBreakdown(ds, driver.driver_id);
    const top3 = e.rows
      .slice(0, 3)
      .map((r) => `${r.category} ${sgd(r.total_amount)}`)
      .join(', ');
    return {
      text: `Last month (${e.month}) you spent ${sgd(e.total)}. Top three: ${top3}.`,
      source: 'expense_breakdown',
    };
  }

  if (/cpf|retire|opt.?in|platform worker/.test(t)) {
    const inc = incomeSummary(ds, driver.driver_id);
    const c = cpfProject(inc.avgMonthlyNet, driver.age >= 31);
    return {
      text: `If you opted in to higher CPF: take-home would move from ${sgd(c.before)} to about ${sgd(c.after)}/mo, but ${sgd(c.retirementGain)}/mo would go to retirement once the operator's ${sgd(c.operatorContribution)} match is counted. It is irreversible — I model it, you decide.`,
      source: 'cpf_project',
    };
  }

  if (/goal|insurance|save|saving/.test(t)) {
    const g = state.goals[0];
    return {
      text: g
        ? `Your focus goal is ${g.name}: ${Math.round((g.current / Math.max(g.target, 1)) * 100)}% funded, ${g.badge}. Weekly need ${sgd1(g.weeklyNeed)}${g.gap > 0 ? `, ${sgd1(g.gap)} short this week` : ''}.`
        : 'No active goals selected yet — set one and I will track it weekly.',
      source: 'goal_tracker',
    };
  }

  if (/window|where.*drive|earn more|shift/.test(t))
    return {
      text: `I do not push you to chase surge. I start from your goal, work out the weekly gap, then point to the windows that cover it — see the focus action on your dashboard.`,
      source: 'plan_actions',
    };

  return {
    text: 'I can answer on your runway, income, spending, goals, earning windows or the CPF opt-in. Try one of those.',
    source: 'supervisor',
  };
}
